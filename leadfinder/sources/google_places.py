"""Betriebe über die Google Places API (New) laden – deutlich vollständiger als OSM.

Benötigt einen API-Key in der Umgebungsvariable GOOGLE_PLACES_API_KEY.
Achtung: Abfragen mit Telefon/Website-Feldern sind kostenpflichtig –
vorher Kontingent/Preise in der Google Cloud Console prüfen.
"""
from __future__ import annotations

import os
import re
import time

import requests

from ..categories import Kategorie
from ..models import Lead
from ..regions import Region, ort_basisnamen

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.addressComponents", "places.nationalPhoneNumber", "places.websiteUri",
    "places.location", "places.businessStatus", "places.googleMapsUri",
    "places.rating", "places.userRatingCount", "nextPageToken",
])


def _komponente(place: dict, typ: str) -> str:
    for c in place.get("addressComponents", []) or []:
        if typ in c.get("types", []):
            return c.get("longText", "")
    return ""


def place_zu_lead(place: dict, kat: Kategorie) -> Lead:
    strasse = " ".join(x for x in (_komponente(place, "route"),
                                   _komponente(place, "street_number")) if x)
    ort = _komponente(place, "locality")
    plz = _komponente(place, "postal_code")
    if not ort:
        m = re.search(r"\b(\d{5})\s+([^,]+)", place.get("formattedAddress", ""))
        if m:
            plz, ort = plz or m.group(1), m.group(2).strip()
    loc = place.get("location") or {}
    return Lead(
        name=(place.get("displayName") or {}).get("text", ""),
        kategorie_key=kat.key,
        kategorie=kat.name,
        einfachheit=kat.einfachheit,
        quelle="Google",
        strasse=strasse,
        plz=plz,
        ort=ort,
        telefon=place.get("nationalPhoneNumber", ""),
        website=place.get("websiteUri", ""),
        bewertung=place.get("rating"),
        anzahl_bewertungen=place.get("userRatingCount"),
        maps_link=place.get("googleMapsUri", ""),
        lat=loc.get("latitude"),
        lon=loc.get("longitude"),
    )


def _suche(text: str, key: str, max_seiten: int = 3) -> list[dict]:
    places: list[dict] = []
    token = None
    for _ in range(max_seiten):
        body = {"textQuery": text, "languageCode": "de", "regionCode": "DE", "pageSize": 20}
        if token:
            body["pageToken"] = token
        r = requests.post(URL, json=body, timeout=30, headers={
            "X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS})
        if r.status_code != 200:
            raise RuntimeError(f"Google Places Fehler {r.status_code}: {r.text[:300]}")
        data = r.json()
        places.extend(data.get("places", []))
        token = data.get("nextPageToken")
        if not token:
            break
        time.sleep(1.5)
    return places


def lade(regionen: list[Region], kategorien: list[Kategorie], log=print) -> list[Lead]:
    key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not key:
        raise SystemExit("GOOGLE_PLACES_API_KEY ist nicht gesetzt (siehe README).")
    erlaubte_orte = ort_basisnamen(regionen)
    gesehen: set[str] = set()
    leads: list[Lead] = []
    for kat in kategorien:
        for begriff in kat.google:
            for region in regionen:
                for ort in region.orte:
                    anfrage = f"{begriff} in {ort}"
                    try:
                        treffer = _suche(anfrage, key)
                    except RuntimeError as e:
                        log(f"  {e}")
                        continue
                    neu = 0
                    for p in treffer:
                        pid = p.get("id")
                        if not pid or pid in gesehen:
                            continue
                        if p.get("businessStatus") == "CLOSED_PERMANENTLY":
                            continue
                        adr = p.get("formattedAddress", "")
                        if not any(o in adr for o in erlaubte_orte):
                            continue  # außerhalb des Suchgebiets
                        gesehen.add(pid)
                        leads.append(place_zu_lead(p, kat))
                        neu += 1
                    log(f"Google: {anfrage!r}: {neu} neue Betriebe")
    return leads
