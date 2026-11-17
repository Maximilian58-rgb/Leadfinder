"""Leadfinder – Betriebe ohne / mit schlechter Website finden und ranken.

Beispiele:
    python -m leadfinder                         # OSM, Rhein-Sieg + Bonn + Köln
    python -m leadfinder --quelle beide          # OSM + Google Places (API-Key nötig)
    python -m leadfinder --regionen rhein-sieg bonn --kategorien garten maler heizung
    python -m leadfinder --liste                 # Kategorien & Regionen anzeigen
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from . import categories, regions, scoring
from . import website_check as wc
from .export import exportiere
from .models import Lead


def _liste() -> None:
    print("Kategorien (sortiert nach Einfachheit):")
    for k in sorted(categories.KATEGORIEN, key=lambda k: -k.einfachheit):
        print(f"  {k.key:<13} {k.einfachheit:>2}/10  {k.name}")
    print("\nRegionen:")
    for r in regions.REGIONEN.values():
        std = " (Standard)" if r.key in regions.STANDARD else ""
        print(f"  {r.key:<13} {r.name}{std}")


def _lade_cache(pfad: Path) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pruefe_websites(leads: list[Lead], cache_pfad: Path, threads: int, log=print) -> None:
    cache = _lade_cache(cache_pfad)
    offen = [l for l in leads if l.website and wc.normalisiere_url(l.website) not in cache
             and not wc.ist_social(l.website)]
    urls = sorted({wc.normalisiere_url(l.website) for l in offen})
    log(f"Prüfe {len(urls)} Websites ({len(cache)} aus Cache) …")
    if urls:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(wc.pruefe, u): u for u in urls}
            for n, f in enumerate(as_completed(futures), 1):
                u = futures[f]
                try:
                    cache[u] = asdict(f.result())
                except Exception as e:  # noqa: BLE001 – eine kaputte Seite darf nicht alles stoppen
                    cache[u] = asdict(wc.Analyse(wc.STATUS_KAPUTT, [f"Fehler: {e}"], 10, u))
                if n % 25 == 0 or n == len(urls):
                    log(f"  {n}/{len(urls)} geprüft")
                    cache_pfad.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    for l in leads:
        if not l.website:
            a = wc.Analyse(wc.STATUS_KEINE, ["Keine Website gefunden"], 0)
        elif wc.ist_social(l.website):
            a = wc.pruefe(l.website)  # ohne Netzwerk
        else:
            a = wc.Analyse(**cache[wc.normalisiere_url(l.website)])
        l.website_status, l.website_maengel = a.status, a.maengel
        l.website_maengel_punkte, l.final_url = a.punkte, a.final_url
        if not l.email and a.emails:
            l.email = wc.beste_email(a.emails, l.website)
        if not l.telefon and a.telefone:
            l.telefon = a.telefone[0]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="leadfinder", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--quelle", choices=["osm", "google", "beide"], default="osm")
    p.add_argument("--regionen", nargs="+", help=f"Standard: {' '.join(regions.STANDARD)}; "
                                                 "'alle' für alle")
    p.add_argument("--kategorien", nargs="+", help="Standard: alle")
    p.add_argument("--ausgabe", default="ergebnisse", help="Ausgabeordner")
    p.add_argument("--ohne-websitecheck", action="store_true",
                   help="Websites nicht laden (schnell, aber keine Qualitätsbewertung)")
    p.add_argument("--ohne-domainsuche", action="store_true",
                   help="Für Betriebe ohne Website NICHT nach passenden Domains suchen")
    p.add_argument("--threads", type=int, default=16)
    p.add_argument("--nur-mit-telefon", action="store_true",
                   help="Betriebe ohne Telefonnummer weglassen")
    p.add_argument("--osm-datei", help="Lokale .osm.pbf-Datei statt Overpass-API nutzen "
                                       "(pip install osmium shapely)")
    p.add_argument("--liste",action="store_true", help="Kategorien/Regionen anzeigen")
    a = p.parse_args(argv)

    if a.liste:
        _liste()
        return 0

    regs = regions.auswahl(a.regionen)
    kats = categories.auswahl(a.kategorien)
    ordner = Path(a.ausgabe)
    ordner.mkdir(parents=True, exist_ok=True)

    leads: list[Lead] = []
    if a.osm_datei:
        from .sources import osm_pbf
        leads += osm_pbf.lade(a.osm_datei, regs, kats)
    elif a.quelle in ("osm", "beide"):
        from .sources import osm
        leads += osm.lade(regs, kats)
    if a.quelle in ("google", "beide"):
        from .sources import google_places
        leads += google_places.lade(regs, kats)
    vorher = len(leads)
    leads = scoring.entferne_ketten(leads)
    print(f"{vorher - len(leads)} Filialketten-Standorte entfernt")
    leads = scoring.dedupliziere(leads)
    print(f"{len(leads)} Betriebe nach Duplikat-Bereinigung")

    if not a.ohne_websitecheck and not a.ohne_domainsuche:
        from .website_suche import ergaenze_websites
        ergaenze_websites(leads, threads=a.threads)

    if a.ohne_websitecheck:
        for l in leads:
            l.website_status = (wc.STATUS_KEINE if not l.website else
                                wc.STATUS_SOCIAL if wc.ist_social(l.website) else
                                wc.STATUS_MITTEL)
    else:
        pruefe_websites(leads, ordner / "website_cache.json", a.threads)

    if a.nur_mit_telefon:
        leads = [l for l in leads if l.telefon]
    for l in leads:
        l.lead_score = scoring.lead_score(l)

    xlsx, csv_pfad = exportiere(leads, ordner)
    from collections import Counter
    st = Counter(l.website_status for l in leads)
    print("\nErgebnis:")
    for s in wc.STATUS_REIHENFOLGE:
        print(f"  {s:<32} {st[s]:>5}")
    print(f"  {'mit Telefon':<32} {sum(1 for l in leads if l.telefon):>5}")
    print(f"  {'mit E-Mail':<32} {sum(1 for l in leads if l.email):>5}")
    print(f"\nExcel: {xlsx}\nCSV:   {csv_pfad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
