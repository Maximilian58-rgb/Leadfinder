"""Website für Betriebe ohne eingetragene Website suchen – ohne Suchmaschine.

OSM/Google kennen oft keine Website, obwohl eine existiert. Wir probieren
naheliegende Domains (z. B. "Malerbetrieb Schmitz" -> malerbetrieb-schmitz.de,
schmitz-maler.de …) und akzeptieren einen Treffer NUR, wenn auf der Seite
(oder deren Impressum/Kontakt) die Telefonnummer oder die Straße + PLZ/Ort des
Betriebs steht. Dadurch kaum Fehltreffer.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup

from . import website_check as wc
from .models import Lead

RECHTSFORMEN = {"gmbh", "ug", "ek", "e", "k", "kg", "ohg", "gbr", "co", "inh", "inhaber",
                "haftungsbeschränkt", "mbh", "ag", "und", "der", "die", "das", "von", "am",
                "an", "im", "in", "zum", "zur", "fa", "firma", "&", "u", "&co"}
GENERISCH = {"friseur", "salon", "bäckerei", "baeckerei", "metzgerei", "kfz", "auto",
             "werkstatt", "service", "haus", "team", "studio", "kosmetik", "nails", "nail",
             "hair", "beauty", "elektro", "sanitär", "sanitaer", "heizung", "maler",
             "garten", "bau", "dach", "meisterbetrieb", "gmbh"}


GENERISCHE_STAEMME = tuple(_s for _s in (
    "maler", "friseur", "baecker", "backstube", "metzger", "fleisch", "elektro", "sanitaer",
    "heizung", "haustechnik", "garten", "galabau", "dach", "bau", "schrein", "tischler",
    "zimmer", "fliesen", "boden", "parkett", "kfz", "auto", "werkstatt", "salon", "haar",
    "hair", "kosmetik", "nagel", "nail", "beauty", "reinigung", "gebaeude", "umzug",
    "schluessel", "glas", "stein", "polster", "raumaus", "metall", "schlosser", "fenster",
    "rolll", "sonnenschutz", "hausmeister", "meister", "service", "studio", "team"))


def _slug(wort: str) -> str:
    w = wort.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("é", "e"), ("è", "e")):
        w = w.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", w)


def kandidaten(name: str, ort: str, max_anzahl: int = 8) -> list[str]:
    roh = re.split(r"[\s\-/,.+()|:'\"]+", name.lower())
    toks = [t for t in roh if t and t not in RECHTSFORMEN]
    toks = [_slug(t) for t in toks]
    toks = [t for t in toks if len(t) >= 2][:4]
    if not toks:
        return []
    ort_s = _slug(re.split(r"[\s(\-]", ort or "")[0]) if ort else ""
    namen: list[str] = []

    def add(*teile: str, sep: str = "-") -> None:
        n = sep.join(t for t in teile if t)
        if 3 <= len(n) <= 50 and n not in namen:
            namen.append(n)

    add(*toks)
    add(*toks, sep="")
    if len(toks) >= 2:
        add(toks[-1], toks[0])
        add(toks[0], toks[1])
        add(toks[0], toks[1], sep="")
    if ort_s:
        add(*toks, ort_s)
        add(*toks[:2], ort_s)
    eigen = [t for t in toks if len(t) >= 5 and not t.startswith(GENERISCHE_STAEMME)]
    if eigen:
        add(eigen[0])
        if ort_s:
            add(eigen[0], ort_s)
    return [f"{n}.de" for n in namen[:max_anzahl]]


def _ziffern(tel: str) -> str:
    d = re.sub(r"\D", "", tel or "")
    if d.startswith("49"):
        d = "0" + d[2:]
    return d.lstrip("0")


def passt(text: str, lead: Lead) -> bool:
    t = text.lower()
    tel = _ziffern(lead.telefon)
    if len(tel) >= 7:
        if tel[-7:] in re.sub(r"\D", "", t):
            return True
    if lead.strasse:
        strasse = lead.strasse.lower().replace("straße", "str").replace("strasse", "str")
        name_teil = re.sub(r"\s*\d.*$", "", strasse).strip()
        t2 = t.replace("straße", "str").replace("strasse", "str")
        if len(name_teil) >= 4 and name_teil in t2:
            if (lead.plz and lead.plz in t) or (lead.ort and lead.ort.lower().split()[0] in t):
                return True
    return False


def finde_website(lead: Lead, timeout: int = 8) -> str:
    if not (lead.telefon or lead.strasse):
        return ""  # nicht verifizierbar
    s = wc.neue_session()
    for dom in kandidaten(lead.name, lead.ort):
        try:
            r = wc.hole(s, f"https://www.{dom}", timeout)
        except wc.Abruffehler:
            continue
        if r.status >= 400 or wc.ist_social(r.url):
            continue
        if passt(r.text, lead):
            return r.url
        soup = BeautifulSoup(r.text, "html.parser")
        for unterseite in wc._kontaktseiten(soup, r.url)[:2]:
            try:
                ru = wc.hole(s, unterseite, timeout)
            except wc.Abruffehler:
                continue
            if ru.status < 400 and passt(ru.text, lead):
                return r.url
    return ""


def ergaenze_websites(leads: list[Lead], threads: int = 24, log=print) -> int:
    ohne = [l for l in leads if not l.website]
    log(f"Domain-Suche für {len(ohne)} Betriebe ohne eingetragene Website …")
    gefunden = 0
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(finde_website, l): l for l in ohne}
        for n, f in enumerate(as_completed(futures), 1):
            l = futures[f]
            try:
                url = f.result()
            except Exception:  # noqa: BLE001
                url = ""
            if url:
                l.website = url
                l.quelle += " (Website per Domain-Suche gefunden)"
                gefunden += 1
            if n % 100 == 0 or n == len(ohne):
                log(f"  {n}/{len(ohne)} durchsucht, {gefunden} Websites gefunden")
    return gefunden
