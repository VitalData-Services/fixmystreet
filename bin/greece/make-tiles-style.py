#!/usr/bin/env python3
"""Make the map style served by the `tiles` compose service from OpenFreeMap's positron style.

The result reads our own Greece tiles, fonts and sprites, has no buildings and no shaded
relief, and labels places in Greek (name:el, then the local name) instead of Latin + Greek.

Usage:
    make-tiles-style.py <positron.json> <output.json>

positron.json: https://tiles.openfreemap.org/styles/positron
"""
import json
import sys

GREEK_NAME = ["coalesce", ["get", "name:el"], ["get", "name"]]


def main(src, dst):
    style = json.load(open(src))
    style["name"] = "FixMyStreets positron"
    style["sources"] = {"openmaptiles": {"type": "vector", "url": "mbtiles://{greece}"}}
    style["glyphs"] = "{fontstack}/{range}.pbf"
    style["sprite"] = "ofm"
    layers = []
    for layer in style["layers"]:
        if layer.get("source") == "ne2_shaded":
            continue
        if layer.get("source-layer") == "building" or layer["type"] == "fill-extrusion":
            continue
        layout = layer.get("layout", {})
        if "name:latin" in json.dumps(layout.get("text-field", "")):
            layout["text-field"] = GREEK_NAME
        layers.append(layer)
    style["layers"] = layers
    with open(dst, "w") as f:
        json.dump(style, f, ensure_ascii=False, indent=1)
    print(f"{len(layers)} layers written to {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
