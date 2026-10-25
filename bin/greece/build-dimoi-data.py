#!/usr/bin/env python3
"""Build the static municipality data used by the homepage minimap.

Writes web/cobrands/greece/dimoi/index.json (name, bbox, a point inside it for the map of
reports on /reports, and contact details per municipality) and one <osm_relation_id>.json boundary file per municipality, so the
browser can find the municipality under the map centre without any third-party call.

Usage:
    build-dimoi-data.py <municipalities.csv> <geometries.json> <output-dir> [<overrides.csv> ...]

municipalities.csv: one row per municipality with at least name_el and osm_rel; optional
website, email_*, phone_* columns (dimoi_base.csv or dimoi_contacts.csv).
geometries.json: {osm_rel: GeoJSON geometry}, e.g. from Nominatim lookup with
polygon_geojson=1&polygon_threshold=0.0005.
overrides.csv: same columns, matched on osm_rel; non-empty values replace the base ones.
Pass dimoi_police.csv as one of them for the municipality's police station (at_name, at_email,
at_phone), which the minimap's card shows with the municipality's contacts, and
dimoi_emails_official.csv for the municipality's official address where there is no other
(email_recommended, the first of kede_phones).
"""
import csv
import json
import os
import re
import sys

from shapely.geometry import shape

CONTACT_FIELDS = [
    ("email_general", "phone_general", "Δήμος"),
    ("email_anafores", "phone_anafores", "Αναφορές πολιτών"),
    ("email_dimotiki_astynomia", "phone_dimotiki_astynomia", "Δημοτική Αστυνομία"),
    ("email_texniki_ypiresia", "phone_texniki_ypiresia", "Τεχνική Υπηρεσία"),
]


def rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    raise ValueError("unsupported geometry " + geom["type"])


def rounded(geom, places=5):
    def r(c):
        return [round(c[0], places), round(c[1], places)]
    polys = [[[r(c) for c in ring] for ring in poly] for poly in rings(geom)]
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": polys[0]}
    return {"type": "MultiPolygon", "coordinates": polys}


def bbox(geom):
    xs, ys = [], []
    for poly in rings(geom):
        for c in poly[0]:
            xs.append(c[0])
            ys.append(c[1])
    return [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]


def label_point(geom):
    """A point inside the municipality, on its largest part (so an island municipality's is not on
    a rock), where reports/index.html puts its count."""
    s = shape(geom)
    if s.geom_type == "MultiPolygon":
        s = max(s.geoms, key=lambda g: g.area)
    p = s.representative_point()
    return [round(p.x, 5), round(p.y, 5)]


def first_phone(text):
    """The first phone number in a list such as "210 5277000, 1595;210 3310861" (a short line like
    1595 is skipped)."""
    m = re.search(r"\+?\d[\d ]{6,}\d", text or "")
    return m.group(0).strip() if m else ""


def police_station(row):
    """The police station from dimoi_police.csv's columns: {"n": name, "e": email, "t": phone}, the phone
    without its label ("Αξιωματικός Υπηρεσίας: 22820 22300") and only the first number. Where the file
    names no station (several in one municipality, as in Αθήνα, or none), its police directorate."""
    name, email = (row.get("at_name") or "").strip(), (row.get("at_email") or "").strip()
    m = re.search(r"\+?\d[\d ]{6,}\d", (row.get("at_phone") or "").split(":")[-1])
    phone = m.group(0).strip() if m else ""
    if not (email or phone):
        name, email = (row.get("directorate") or "").strip(), (row.get("directorate_email") or "").strip()
        if not email:
            return None
    return {"n": name or "Αστυνομικό Τμήμα", **({"e": email} if email else {}), **({"t": phone} if phone else {})}


def load_rows(csv_path, override_paths):
    rows = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            rows[row["osm_rel"]] = row
    for path in override_paths:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                base = rows.setdefault(row["osm_rel"], {})
                base.update({k: v for k, v in row.items() if v})
    return rows.values()


def main(csv_path, geoms_path, out_dir, *override_paths):
    geoms = json.load(open(geoms_path))
    os.makedirs(out_dir, exist_ok=True)
    index = []
    for row in load_rows(csv_path, override_paths):
        rel = row["osm_rel"]
        geom = geoms.get(rel)
        if not geom:
            print("no geometry for", rel, row["name_el"], file=sys.stderr)
            continue
        entry = {"r": int(rel), "n": row["name_el"], "b": bbox(geom), "p": label_point(geom)}
        if row.get("website"):
            entry["w"] = row["website"]
        if not (row.get("email_general") or "").strip() and (row.get("email_recommended") or "").strip():
            row["email_general"] = row["email_recommended"].strip()
            row["phone_general"] = first_phone(row.get("kede_phones"))
        contacts = []
        for email_col, phone_col, label in CONTACT_FIELDS:
            email, phone = (row.get(email_col) or "").strip(), (row.get(phone_col) or "").strip()
            if email or phone:
                contacts.append({"l": label, **({"e": email} if email else {}), **({"t": phone} if phone else {})})
        if contacts:
            entry["c"] = contacts
        police = police_station(row)
        if police:
            entry["a"] = police
        index.append(entry)
        with open(os.path.join(out_dir, rel + ".json"), "w") as g:
            json.dump(rounded(geom), g, separators=(",", ":"))
    with open(os.path.join(out_dir, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(index)} municipalities written to {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
