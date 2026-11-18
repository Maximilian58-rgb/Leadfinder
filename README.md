# Leadfinder – Handwerk & Dienstleister ohne (gute) Website

Findet Betriebe (Gartenpflege, Maler, Heizung/Sanitär, Elektriker, Dachdecker, …) im
**Rhein-Sieg-Kreis, Bonn und Köln** (optional auch Rhein-Erft, Rhein-Berg, Ahrweiler),
prüft deren Website und rankt sie als Verkaufs-Leads für Webdesign, mit **Telefon und E-Mail**.

## Was rauskommt

`ergebnisse/leads.xlsx` mit **einem Blatt „Unternehmen“**, einer langen Liste aller Betriebe:

| Unternehmen | Straße | PLZ | Ort | Telefon | E-Mail | Website | Website-Status | Branche | Mängel der Website | Lead-Score |
|---|---|---|---|---|---|---|---|---|---|---|

- Links steht der Name (fett, bleibt beim Scrollen stehen), rechts daneben die Kontaktdaten.
- Sortiert nach Verkaufschance, beste zuerst, nicht nach Branche. Über den Filter in der
  Kopfzeile kannst du nach Name A–Z sortieren oder z. B. nur „Keine Website“ anzeigen.
- Telefon, E-Mail und Website sind anklickbar.
- Website-Status: Keine Website, Nur Social Media / Verzeichnis, Website kaputt / Platzhalter,
  Schlechte Website, Verbesserungswürdige Website, Gute Website.
- Die Spalte „Mängel“ nennt konkrete Schwächen („Kein HTTPS“, „Nicht mobil-optimiert“,
  „Copyright-Jahr 2014“, „Kein Impressum-Link“) als Gesprächseinstieg.

Zusätzlich gibt es `leads.csv` (Semikolon, für Excel/CRM) mit denselben Spalten.

### Einfachheits-Ranking der Branchen

| Einfachheit | Branchen |
|---|---|
| 9 | Gartenpflege/GaLaBau, Hausmeisterservice, Gebäudereinigung, Maler, Schornsteinfeger |
| 8 | Fliesenleger, Bodenleger, Schlüsseldienst, Glaserei, Steinmetz, Raumausstatter |
| 7 | Schreiner, Dachdecker/Zimmerer, Bau/Maurer, Elektriker, Metallbau, Fenster/Rollläden, Umzug |
| 6 | Bäcker/Metzger, Heizung/Sanitär (SHK), Friseur, Kosmetik |
| 5 | Kfz-Werkstatt |

Anpassen in `leadfinder/categories.py`.

### Lead-Score (0–100)

- Website-Chance (max. 45): keine Website 45, nur Social 42, kaputt 40, schlecht 33, mittel 18, gut 3
- Einfachheit × 3 (max. 30)
- Telefon vorhanden +12, E-Mail vorhanden +8
- Google-Bewertungen (aktiver Betrieb) bis +5

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Benutzung

```bash
# Kostenlos über OpenStreetMap: Rhein-Sieg + Bonn + Köln, alle Branchen
python -m leadfinder

# Nur bestimmte Branchen / Regionen
python -m leadfinder --kategorien garten maler heizung --regionen rhein-sieg bonn

# Alle Regionen inkl. Nachbarkreise
python -m leadfinder --regionen alle

# Mehr Treffer: zusätzlich Google Places (API-Key nötig, s. u.)
python -m leadfinder --quelle beide

# Nur Betriebe mit Telefonnummer
python -m leadfinder --nur-mit-telefon

# Liste aller Kategorien- und Regions-Kürzel
python -m leadfinder --liste
```

Wenn die Overpass-API überlastet oder gesperrt ist (z. B. in Cloud-Umgebungen), den
OSM-Auszug herunterladen und lokal auswerten (`pip install osmium shapely`):

```bash
curl -o daten/koln.osm.pbf https://download.openstreetmap.fr/extracts/europe/germany/nordrhein_westfalen/koln-latest.osm.pbf
python -m leadfinder --osm-datei daten/koln.osm.pbf
```

Der Auszug „Regierungsbezirk Köln“ deckt Rhein-Sieg-Kreis, Bonn, Köln, Rhein-Erft und
Rhein-Berg ab.

### Was automatisch bereinigt/ergänzt wird

- **Filialketten raus**: Betriebe mit Marken-Tag in OSM oder ≥ 3 gleichnamigen Standorten
  (Kamps, BackWerk, …) haben Konzern-Websites und sind keine Kunden.
- **Duplikate** aus OSM + Google werden zusammengeführt.
- **Domain-Suche**: Für Betriebe ohne eingetragene Website werden naheliegende Domains
  probiert (z. B. `malerbetrieb-schmitz.de`). Ein Treffer zählt nur, wenn Telefonnummer oder
  Straße + PLZ/Ort des Betriebs auf der Seite stehen. Abschalten mit `--ohne-domainsuche`.
- **E-Mail/Telefon** werden aus Startseite, Impressum und Kontaktseite gelesen.

Die Website-Prüfung wird in `ergebnisse/website_cache.json` gespeichert. Ein zweiter Lauf ist
dadurch schnell. Den Cache löschen, wenn die Seiten neu geprüft werden sollen.

### Datenquellen

- **OpenStreetMap** (Standard): kostenlos, ohne Anmeldung. Gut für den Einstieg, aber nicht
  jeder Handwerker ist in OSM eingetragen, und Telefon/E-Mail fehlen oft.
- **Google Places** (`--quelle google` oder `beide`): findet deutlich mehr Betriebe, liefert
  fast immer die Telefonnummer, dazu Bewertungen. Dafür in der Google Cloud Console die
  „Places API (New)“ aktivieren, einen API-Key erstellen und setzen:
  ```bash
  export GOOGLE_PLACES_API_KEY="..."      # Windows: set GOOGLE_PLACES_API_KEY=...
  ```
  Die Abfragen sind kostenpflichtig. Vorher in der Cloud Console die aktuellen Preise bzw.
  das Freikontingent prüfen und ein Budget-Limit setzen. Ein voller Lauf macht ca.
  (Suchbegriffe × Orte) Anfragen, also mehrere tausend; zum Testen erst mit
  `--kategorien garten --regionen bonn` starten.

E-Mail-Adressen werden, wenn nicht in OSM/Google vorhanden, aus der Website (Startseite,
Impressum, Kontakt) gelesen. **Betriebe ohne Website haben meist keine öffentliche E-Mail**,
für die ist das Telefon der Kanal.

## Rechtlicher Hinweis (Kaltakquise)

- **E-Mail-Werbung** an Firmen ohne vorherige Einwilligung ist in Deutschland
  (§ 7 Abs. 2 UWG) grundsätzlich unzulässig und abmahnfähig.
- **Telefon-Akquise** bei Gewerbetreibenden ist bei *mutmaßlicher Einwilligung* erlaubt,
  also wenn ein konkreter, sachlicher Bezug zum Betrieb besteht (z. B. eine nicht erreichbare
  Website oder ein fehlendes Impressum). Die Mängelliste hilft dir, diesen Bezug zu benennen.
- Briefpost und persönlicher Besuch sind unkritisch.
- Kontaktdaten nur für diesen Zweck speichern und auf Wunsch löschen (DSGVO).

Das ist keine Rechtsberatung. Im Zweifel bei IHK oder Anwalt nachfragen.

## Tests

```bash
pip install pytest && python -m pytest -q
```
