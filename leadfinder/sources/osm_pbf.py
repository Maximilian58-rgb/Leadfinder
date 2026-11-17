"""Betriebe aus einem heruntergeladenen OSM-Auszug (.osm.pbf) laden.

Alternative zur Overpass-API, wenn diese überlastet/gesperrt ist. Benötigt
`pip install osmium shapely`. Passender Auszug für Bonn/Köln/Rhein-Sieg:
https://download.openstreetmap.fr/extracts/europe/germany/nordrhein_westfalen/koln-latest.osm.pbf
(oder Geofabrik: .../nordrhein-westfalen/koeln-regbez-latest.osm.pbf)
"""
from __future__ import annotations

from pathlib import Path

from ..categories import Kategorie, kategorie_fuer_tags
from ..models import Lead
from ..regions import Region
from .osm import element_zu_lead

PBF_URL = ("https://download.openstreetmap.fr/extracts/europe/germany/"
           "nordrhein_westfalen/koln-latest.osm.pbf")


def lade(pfad: str | Path, regionen: list[Region], kategorien: list[Kategorie],
         log=print) -> list[Lead]:
    import osmium
    from shapely import wkb
    from shapely.geometry import Point
    from shapely.prepared import prep

    keys = {k.key for k in kategorien}
    gesucht = {(r.name, r.admin_level): r for r in regionen}
    grenzen: dict[str, object] = {}
    gemeinden: list[tuple[str, object]] = []   # admin_level 8 -> echter Ortsname
    kandidaten: list[dict] = []
    fab = osmium.geom.WKBFactory()

    log(f"OSM-Datei: lese {pfad} …")
    fp = (osmium.FileProcessor(str(pfad))
          .with_locations()
          .with_areas(osmium.filter.TagFilter(("boundary", "administrative")))
          .with_filter(osmium.filter.KeyFilter("craft", "shop", "office", "boundary")))
    for obj in fp:
        tags = {t.k: t.v for t in obj.tags}
        if obj.is_area():
            if not obj.from_way() and tags.get("boundary") == "administrative":
                r = gesucht.get((tags.get("name"), tags.get("admin_level")))
                try:
                    if r:
                        grenzen[r.name] = prep(wkb.loads(fab.create_multipolygon(obj), hex=True))
                    elif tags.get("admin_level") == "8" and tags.get("name"):
                        gemeinden.append((tags["name"], prep(
                            wkb.loads(fab.create_multipolygon(obj), hex=True))))
                except RuntimeError:
                    pass  # unvollständige Grenze am Dateirand
            continue
        if obj.is_relation() or kategorie_fuer_tags(tags) is None:
            continue
        if obj.is_node():
            if not obj.location.valid():
                continue
            lat, lon, typ = obj.location.lat, obj.location.lon, "node"
        else:  # Way (meist Gebäude-Umriss) -> Mittelpunkt der Knoten
            pts = [n.location for n in obj.nodes if n.location.valid()]
            if not pts:
                continue
            lat = sum(p.lat for p in pts) / len(pts)
            lon = sum(p.lon for p in pts) / len(pts)
            typ = "way"
        kandidaten.append({"type": typ, "id": obj.id, "lat": lat, "lon": lon, "tags": tags})

    fehlend = [r.name for r in regionen if r.name not in grenzen]
    if fehlend:
        log(f"  Warnung: Grenzen nicht in der Datei: {', '.join(fehlend)}")
    leads: list[Lead] = []
    for el in kandidaten:
        pt = Point(el["lon"], el["lat"])
        region = next((n for n, g in grenzen.items() if g.contains(pt)), None)
        if not region:
            continue
        lead = element_zu_lead(el, keys)
        if lead:
            if not lead.ort:
                lead.ort = next((n for n, g in gemeinden if g.contains(pt)), region)
            leads.append(lead)
    log(f"  {len(leads)} Betriebe im Suchgebiet gefunden")
    return leads
