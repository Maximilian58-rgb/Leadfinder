"""Website-Prüfung: erreichbar? veraltet? mobilfähig? + E-Mail/Telefon finden."""
from __future__ import annotations

import datetime as _dt
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

STATUS_KEINE = "Keine Website"
STATUS_SOCIAL = "Nur Social Media / Verzeichnis"
STATUS_KAPUTT = "Website kaputt / Platzhalter"
STATUS_SCHLECHT = "Schlechte Website"
STATUS_MITTEL = "Verbesserungswürdige Website"
STATUS_GUT = "Gute Website"

# Reihenfolge = Verkaufschance (oben = beste Chance)
STATUS_REIHENFOLGE = [STATUS_KEINE, STATUS_SOCIAL, STATUS_KAPUTT, STATUS_SCHLECHT,
                      STATUS_MITTEL, STATUS_GUT]

SOCIAL_DOMAINS = (
    "facebook.com", "fb.com", "instagram.com", "linkedin.com", "xing.com", "tiktok.com",
    "twitter.com", "x.com", "youtube.com", "gelbeseiten.de", "dasoertliche.de", "11880.com",
    "my-hammer.de", "myhammer.de", "werkenntdenbesten.de", "golocal.de", "yelp.de",
    "google.com", "goo.gl", "g.page", "business.site", "linktr.ee", "meinestadt.de",
    "branchenbuch", "cylex.de", "wlw.de", "handwerk.de", "houzz.de",
)
BAUKASTEN_DOMAINS = (
    "jimdofree.com", "jimdo.com", "jimdosite.com", "wixsite.com", "weebly.com",
    "webnode.page", "webnode.com", "npage.de", "beepworld.de", "homepage-t-online.de",
    "page4.com", "site123.me", "wordpress.com", "blogspot.com", "strikingly.com",
    "one.com/", "carrd.co", "ueniweb.com", "ionos.space",
)
PLATZHALTER_MUSTER = re.compile(
    r"(domain (is|ist) (for sale|zu verkaufen)|diese domain (kann|steht)|"
    r"under construction|im aufbau|baustelle|coming soon|demnächst online|"
    r"website (ist )?in (kürze|arbeit)|hier entsteht|parked domain|domain parking|"
    r"this domain (has been|is) (registered|parked)|default web site page|"
    r"it works!|index of /|apache2 (ubuntu|debian) default page|welcome to nginx)",
    re.I,
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
EMAIL_OBFUSKIERT = re.compile(
    r"([A-Za-z0-9._%+\-]+)\s*(?:\(at\)|\[at\]|\{at\}| at |\(ät\)|@)\s*"
    r"([A-Za-z0-9\-]+)\s*(?:\(dot\)|\[dot\]|\(punkt\)|\[punkt\]| dot | punkt |\.)\s*"
    r"([A-Za-z]{2,})", re.I)
EMAIL_BLACKLIST = ("@example.", "@beispiel.de", "@domain.de", "@domain.com", "sentry", "wixpress", "@2x", ".png",
                   ".jpg", ".jpeg", ".gif", ".webp", ".svg", "your@", "ihre@", "name@",
                   "email@", "e-mail@", "max@mustermann", "mustermann")
TEL_RE = re.compile(r"(?:\+49|0049|\b0)[\s/\-().]*\d{2,5}[\s/\-().]*\d{3,}[\d\s/\-]{0,10}")
JAHR_RE = re.compile(r"(?:©|&copy;|copyright|\(c\))\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", re.I)
JQUERY_RE = re.compile(r"jquery[.-]?(\d)\.(\d+)", re.I)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


@dataclass
class Analyse:
    status: str
    maengel: list[str] = field(default_factory=list)
    punkte: int = 0
    final_url: str = ""
    emails: list[str] = field(default_factory=list)
    telefone: list[str] = field(default_factory=list)


def normalisiere_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url.lstrip("/")
    return url


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def ist_social(url: str) -> bool:
    d = _domain(normalisiere_url(url))
    return any(d == s or d.endswith("." + s) or s in d for s in SOCIAL_DOMAINS)


def finde_emails(html: str, soup: BeautifulSoup | None = None) -> list[str]:
    gefunden: list[str] = []
    if soup is not None:
        for a in soup.select('a[href^="mailto:"]'):
            adr = a["href"][7:].split("?")[0].strip()
            if adr:
                gefunden.append(adr)
    text = soup.get_text(" ") if soup is not None else html
    gefunden += EMAIL_RE.findall(text)
    gefunden += [f"{a}@{b}.{c}" for a, b, c in EMAIL_OBFUSKIERT.findall(text)]
    sauber: list[str] = []
    for e in gefunden:
        e = e.strip().strip(".,;:").lower()
        if "@" not in e or any(b in e for b in EMAIL_BLACKLIST):
            continue
        if e not in sauber:
            sauber.append(e)
    return sauber


def finde_telefone(soup: BeautifulSoup) -> list[str]:
    out: list[str] = []
    for a in soup.select('a[href^="tel:"]'):
        nr = a["href"][4:].strip()
        if nr and nr not in out:
            out.append(nr)
    if not out:
        for m in TEL_RE.findall(soup.get_text(" ")):
            nr = re.sub(r"\s+", " ", m).strip(" -/")
            if len(re.sub(r"\D", "", nr)) >= 7 and nr not in out:
                out.append(nr)
            if len(out) >= 3:
                break
    return out


def bewerte_html(html: str, final_url: str, ladezeit: float = 0.0,
                 jahr_heute: int | None = None) -> Analyse:
    """Reine HTML-Bewertung (ohne Netzwerk) – liefert Mängelliste und Punkte."""
    jahr_heute = jahr_heute or _dt.date.today().year
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    woerter = len(text.split())
    maengel: list[tuple[str, int]] = []

    if len(html) < 300 or PLATZHALTER_MUSTER.search(text[:3000]) and woerter < 400:
        return Analyse(STATUS_KAPUTT, ["Platzhalter-/Baustellen-/Parkseite"], 10, final_url,
                       finde_emails(html, soup), finde_telefone(soup))

    if final_url.startswith("http://"):
        maengel.append(("Kein HTTPS (Browser zeigt 'Nicht sicher')", 3))
    if not soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)}):
        maengel.append(("Nicht mobil-optimiert (kein Viewport)", 3))
    if soup.find(["frameset", "frame"]) or soup.find("iframe", attrs={"name": "main"}):
        maengel.append(("Veraltete Frames-Technik", 3))
    if soup.find(["marquee", "blink", "font", "center"]):
        maengel.append(("Veraltetes HTML (font/center/marquee)", 2))
    if re.search(r"\.swf\b|shockwave-flash", html, re.I):
        maengel.append(("Flash-Inhalte", 3))
    tabellen = len(soup.find_all("table"))
    if tabellen >= 4 and not soup.find(["header", "nav", "main", "section", "footer"]):
        maengel.append(("Tabellen-Layout (90er/2000er-Stil)", 2))

    jahre = [int(j) for j in JAHR_RE.findall(html) if int(j) <= jahr_heute]
    if jahre:
        juengstes = max(jahre)
        alter = jahr_heute - juengstes
        if alter >= 5:
            maengel.append((f"Copyright-Jahr {juengstes} (seit {alter} J. nicht gepflegt)", 3))
        elif alter >= 3:
            maengel.append((f"Copyright-Jahr {juengstes}", 1))

    m = JQUERY_RE.search(html)
    if m and (int(m.group(1)), int(m.group(2))) < (1, 9):
        maengel.append((f"Sehr alte jQuery-Version {m.group(1)}.{m.group(2)}", 1))

    gen = soup.find("meta", attrs={"name": re.compile("^generator$", re.I)})
    gen_txt = (gen.get("content") or "") if gen else ""
    if re.search(r"frontpage|dreamweaver|netobjects|homepage ?baukasten|web\.de|"
                 r"1&1 ?(website|mywebsite)|joomla! 1\.|wordpress [2-4]\.", gen_txt, re.I):
        maengel.append((f"Veralteter Generator: {gen_txt[:40]}", 2))

    d = _domain(final_url)
    if any(b in d for b in BAUKASTEN_DOMAINS):
        maengel.append(("Kostenlose Baukasten-Subdomain (unprofessionell)", 3))

    titel = soup.title.get_text(strip=True) if soup.title else ""
    if not titel or titel.lower() in ("home", "startseite", "willkommen", "index"):
        maengel.append(("Kein aussagekräftiger Seitentitel (SEO)", 1))
    if not soup.find("meta", attrs={"name": re.compile("^description$", re.I)}):
        maengel.append(("Keine Meta-Description (SEO)", 1))
    if woerter < 120:
        maengel.append(("Sehr wenig Inhalt", 2))
    if not soup.find("a", string=re.compile("impressum", re.I)) and \
            not soup.find("a", href=re.compile("impressum", re.I)):
        maengel.append(("Kein Impressum-Link gefunden (Abmahnrisiko)", 2))
    if not re.search(r"datenschutz|privacy", html, re.I):
        maengel.append(("Keine Datenschutzerklärung (DSGVO-Risiko)", 2))
    if ladezeit > 5:
        maengel.append((f"Langsam ({ladezeit:.1f}s)", 2))
    elif ladezeit > 3:
        maengel.append((f"Etwas langsam ({ladezeit:.1f}s)", 1))
    bilder = soup.find_all("img")
    if bilder and sum(1 for b in bilder if not b.get("alt")) / len(bilder) > 0.7:
        maengel.append(("Bilder ohne Alt-Texte", 1))

    punkte = sum(p for _, p in maengel)
    if punkte >= 7:
        status = STATUS_SCHLECHT
    elif punkte >= 3:
        status = STATUS_MITTEL
    else:
        status = STATUS_GUT
    return Analyse(status, [t for t, _ in maengel], punkte, final_url,
                   finde_emails(html, soup), finde_telefone(soup))


def _kontaktseiten(soup: BeautifulSoup, basis: str) -> list[str]:
    urls: list[str] = []
    for a in soup.find_all("a", href=True):
        label = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
        if re.search(r"impressum|kontakt|contact|imprint", label):
            u = urljoin(basis, a["href"])
            if _domain(u) == _domain(basis) and u not in urls:
                urls.append(u)
    return urls[:3]


def pruefe(url: str, timeout: int = 12) -> Analyse:
    """Lädt die Website (inkl. Impressum/Kontakt) und bewertet sie."""
    if not url:
        return Analyse(STATUS_KEINE, ["Keine Website hinterlegt"], 0)
    if ist_social(url):
        return Analyse(STATUS_SOCIAL, [f"Nur Profil auf {_domain(normalisiere_url(url))}"],
                       0, normalisiere_url(url))
    url = normalisiere_url(url)
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9"})
    start = time.monotonic()
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True)
    except requests.exceptions.SSLError:
        try:
            r = s.get(url.replace("https://", "http://"), timeout=timeout)
        except requests.RequestException as e:
            return Analyse(STATUS_KAPUTT, [f"Nicht erreichbar ({type(e).__name__})"], 10, url)
    except requests.RequestException as e:
        return Analyse(STATUS_KAPUTT, [f"Nicht erreichbar ({type(e).__name__})"], 10, url)
    ladezeit = time.monotonic() - start
    if r.status_code >= 400:
        return Analyse(STATUS_KAPUTT, [f"Fehlerseite HTTP {r.status_code}"], 10, r.url)
    if ist_social(r.url):
        return Analyse(STATUS_SOCIAL, [f"Leitet weiter auf {_domain(r.url)}"], 0, r.url)
    r.encoding = r.encoding or r.apparent_encoding
    analyse = bewerte_html(r.text, r.url, ladezeit)

    # Impressum/Kontakt nach E-Mail & Telefon durchsuchen
    if analyse.status != STATUS_KAPUTT:
        soup = BeautifulSoup(r.text, "html.parser")
        for unterseite in _kontaktseiten(soup, r.url):
            try:
                ru = s.get(unterseite, timeout=timeout)
            except requests.RequestException:
                continue
            if ru.status_code >= 400:
                continue
            ru.encoding = ru.encoding or ru.apparent_encoding
            sub = BeautifulSoup(ru.text, "html.parser")
            for e in finde_emails(ru.text, sub):
                if e not in analyse.emails:
                    analyse.emails.append(e)
            for t in finde_telefone(sub):
                if t not in analyse.telefone:
                    analyse.telefone.append(t)
    return analyse


def beste_email(emails: list[str], website: str) -> str:
    """Bevorzugt Adressen der eigenen Domain und info@/kontakt@."""
    if not emails:
        return ""
    dom = _domain(normalisiere_url(website)) if website else ""

    def rang(e: str) -> tuple:
        lokal, _, edom = e.partition("@")
        return (
            0 if dom and edom.endswith(dom) else 1,
            0 if lokal in ("info", "kontakt", "mail", "office", "post", "service") else 1,
            len(e),
        )
    return sorted(emails, key=rang)[0]
