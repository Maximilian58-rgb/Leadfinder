"""Betriebe aus OpenStreetMap (Overpass API) laden – kostenlos, ohne API-Key."""
from __future__ import annotations

import time

import requests

from ..categories import Kategorie, kategorie_fuer_tags
from ..models import Lead
from ..regions import Region

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
USER_AGENT = "Leadfinder/1.0 (lokales Recherche-Tool)"


def build_query(region: Region, kategorien: list[Kategorie]) -> str:
    # Tags gruppieren: craft -> {painter, roofer, ...}
    gruppen: dict[str, set[str]] = {}
    for k in kategorien:
        for tag, wert in k.osm:
            gruppen.setdefault(tag, set()).add(wert)
    teile = []
    for tag, werte in sorted(gruppen.items()):
        regex = "|".join(sorted(werte))
        teile.append(f'  nwr(area.a)["{tag}"~"^({regex})$"];')
    return (
        "[out:json][timeout:300];\n"
        f'area["boundary"="administrative"]["admin_level"="{region.admin_level}"]'
        f'["name"="{region.name}"]->.a;\n'
        "(\n" + "\n".join(teile) + "\n);\n"
        "out center tags;"
    )


def _post(query: str, log) -> dict:
    letzter_fehler: Exception | None = None
    for versuch in range(3):
        for url in OVERPASS_URLS:
            try:
                r = requests.post(url, data={"data": query}, timeout=360,
                                  headers={"User-Agent": USER_AGENT})
                if r.status_code == 200:
                    return r.json()
                letzter_fehler = RuntimeError(f"{url}: HTTP {r.status_code}")
            except requests.RequestException as e:
                letzter_fehler = e
            log(f"  Overpass-Fehler ({letzter_fehler}), versuche nächsten Server …")
        time.sleep(10 * (versuch + 1))
    raise RuntimeError(f"Overpass nicht erreichbar: {letzter_fehler}")


def _first(tags: dict, *keys: str) -> str:
    for k in keys:
        v = tags.get(k)
        if v:
            return str(v).split(";")[0].strip()
    return ""


def element_zu_lead(el: dict, kategorien_keys: set[str]) -> Lead | None:
    tags = el.get("tags") or {}
    name = tags.get("name") or tags.get("brand") or tags.get("operator")
    if not name:
        return None
    if tags.get("disused") == "yes" or tags.get("opening_hours") == "closed":
        return None
    kat = kategorie_fuer_tags(tags)
    if kat is None or kat.key not in kategorien_keys:
        return None
    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lon = el.get("lon") or (el.get("center") or {}).get("lon")
    strasse = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
    return Lead(
        name=name,
        kategorie_key=kat.key,
        kategorie=kat.name,
        einfachheit=kat.einfachheit,
        quelle="OpenStreetMap",
        strasse=strasse,
        plz=tags.get("addr:postcode", ""),
        ort=tags.get("addr:city", "") or tags.get("addr:place", ""),
        telefon=_first(tags, "phone", "contact:phone", "contact:mobile", "mobile"),
        email=_first(tags, "email", "contact:email"),
        website=_first(tags, "website", "contact:website", "url",
                       "contact:facebook", "facebook", "contact:instagram"),
        maps_link=f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
        lat=lat,
        lon=lon,
    )


def lade(regionen: list[Region], kategorien: list[Kategorie], log=print) -> list[Lead]:
    keys = {k.key for k in kategorien}
    leads: list[Lead] = []
    for region in regionen:
        log(f"OSM: lade {region.name} …")
        daten = _post(build_query(region, kategorien), log)
        neu = [l for el in daten.get("elements", []) if (l := element_zu_lead(el, keys))]
        for l in neu:
            if not l.ort:
                l.ort = region.name
        log(f"  {len(neu)} Betriebe gefunden")
        leads.extend(neu)
        time.sleep(2)
    return leads
