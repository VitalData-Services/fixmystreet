"""Local answers to the MapIt calls FixMyStreet makes, for the Greek municipalities (type O07).

Global MapIt takes about half a second per call, and FixMyStreet makes one for every map page and
report form. This service answers from the municipality boundaries in data/ instead, but only
when the answer cannot differ from global MapIt's; anything else goes to global MapIt unchanged.

- point/4326/<lon>,<lat>: answered here only if the point is inside a municipality and no other
  municipality and no coastline is within MARGIN of it. The boundaries in data/geoms.json are
  simplified OpenStreetMap ones, so near a boundary they can be off by up to a hundred metres or
  so; those points, and points just off the coast (piers, beaches), go to global MapIt.
- area/<id>, areas/<ids>: global MapIt's own records for the 328 areas (data/areas.json).
- Everything else, and any request with options this service does not know, is proxied.

data/geoms.json: OSM relation id -> GeoJSON (simplified boundaries of the 332 municipalities).
data/mapit_ids.json: OSM relation id -> the global MapIt area that FixMyStreet's bodies use. Corfu
and Kefalonia have one MapIt area for their three municipalities each, as on global MapIt.
data/areas.json: global MapIt's answer to areas/<all 328 ids>.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import shapely.geometry
from shapely.strtree import STRtree

DATA = os.environ.get("MAPIT_LOCAL_DATA", "/data")
UPSTREAM = os.environ.get("MAPIT_UPSTREAM", "https://global.mapit.mysociety.org").rstrip("/")
# In degrees: about 330 m north-south and 260 m east-west at Greek latitudes.
MARGIN = float(os.environ.get("MAPIT_LOCAL_MARGIN", "0.003"))
TYPE = "O07"
# Query options that do not change the answer for our areas; anything else is proxied.
KNOWN_OPTIONS = {"type", "generation"}

with open(os.path.join(DATA, "geoms.json")) as f:
    geoms = json.load(f)
with open(os.path.join(DATA, "mapit_ids.json")) as f:
    osm_area = json.load(f)
with open(os.path.join(DATA, "areas.json")) as f:
    AREAS = {int(k): v for k, v in json.load(f).items()}

polygons, polygon_area = [], []
for osm_id, geometry in geoms.items():
    info = osm_area.get(osm_id)
    if not info or info.get("id") not in AREAS:
        continue
    shape = shapely.geometry.shape(geometry)  # keeps holes (municipalities inside others)
    if not shape.is_valid:
        shape = shape.buffer(0)
    for part in getattr(shape, "geoms", [shape]):
        if not part.is_empty:
            polygons.append(part)
            polygon_area.append(info["id"])
tree = STRtree(polygons)


def local_area(lon, lat):
    """The area id at the point when it is certain, else None."""
    disc = shapely.geometry.Point(lon, lat).buffer(MARGIN)
    near = tree.query(disc, predicate="intersects")
    if len({polygon_area[i] for i in near}) != 1:
        return None  # another municipality within the margin, or none at all
    for i in near:
        if polygons[i].contains(disc):
            return polygon_area[i]
    return None  # a boundary (coastline) within the margin


class Handler(BaseHTTPRequestHandler):
    server_version = "mapit-local"

    def log_message(self, fmt, *args):
        pass

    def send(self, status, body, how, t0):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(f"{how} {status} {(time.monotonic() - t0) * 1000:.0f}ms {self.path}", flush=True)

    def proxy(self, t0):
        req = urllib.request.Request(UPSTREAM + self.path, headers={"User-Agent": "fixmystreets.gr mapit-local"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.send(resp.status, resp.read(), "upstream", t0)
        except urllib.error.HTTPError as e:
            self.send(e.code, e.read(), "upstream", t0)
        except Exception as e:  # noqa: BLE001 - any failure is a 502 to FixMyStreet
            self.send(502, {"error": f"upstream unavailable: {e.__class__.__name__}"}, "upstream", t0)

    def do_GET(self):
        t0 = time.monotonic()
        url = urllib.parse.urlsplit(self.path)
        path = url.path.strip("/")
        if path.endswith(".json"):
            path = path[:-5]
        query = urllib.parse.parse_qs(url.query)
        if path == "health":
            return self.send(200, {"ok": True, "areas": len(AREAS), "polygons": len(polygons)}, "local", t0)
        if set(query) - KNOWN_OPTIONS:
            return self.proxy(t0)
        types = {t for v in query.get("type", []) for t in v.split(",") if t}

        parts = path.split("/")
        if len(parts) == 3 and parts[0] == "point" and parts[1] == "4326" and (not types or TYPE in types):
            try:
                lon, lat = (float(x) for x in parts[2].split(","))
            except ValueError:
                return self.proxy(t0)
            area = local_area(lon, lat)
            if area is not None:
                return self.send(200, {str(area): AREAS[area]}, "local", t0)
        elif len(parts) == 2 and parts[0] == "area" and parts[1].isdigit() and int(parts[1]) in AREAS:
            return self.send(200, AREAS[int(parts[1])], "local", t0)
        elif len(parts) == 2 and parts[0] == "areas" and set(parts[1].split(",")) == {TYPE}:
            # The list of all areas of our type (admin body form, "Area covered"): ours only. Global MapIt would
            # answer with every country's level-7 areas (Korean districts, ...).
            return self.send(200, {str(k): v for k, v in AREAS.items()}, "local", t0)
        elif len(parts) == 2 and parts[0] == "areas":
            ids = [x for x in parts[1].split(",") if x]
            if ids and all(x.isdigit() and int(x) in AREAS for x in ids):
                return self.send(200, {x: AREAS[int(x)] for x in ids}, "local", t0)
        return self.proxy(t0)


if __name__ == "__main__":
    port = int(os.environ.get("MAPIT_PORT", "8080"))
    print(f"mapit-local: {len(AREAS)} areas, {len(polygons)} polygons, margin {MARGIN}, upstream {UPSTREAM}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
    sys.exit(1)
