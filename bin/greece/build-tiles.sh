#!/bin/sh
# Build the self-hosted map used by every map on the site (homepage minimap and report maps):
# Greece vector tiles in the OpenMapTiles schema, plus the fonts and sprites of the positron
# style, served (and rendered to raster for the report maps) by the `tiles` compose service.
#
# Usage: bin/greece/build-tiles.sh [tiles-dir]   (default /opt/tiles; re-run to refresh OSM data)
# Then:  docker compose restart tiles
set -eu

DIR=${1:-/opt/tiles}
PLANETILER=ghcr.io/onthegomap/planetiler:0.10.2
OFM=https://tiles.openfreemap.org
mkdir -p "$DIR/data" "$DIR/fonts" "$DIR/sprites"

# Fonts the style uses, all glyph ranges, as served by OpenFreeMap (Noto, SIL OFL).
for font in "Noto Sans Regular" "Noto Sans Bold" "Noto Sans Italic"; do
    mkdir -p "$DIR/fonts/$font"
    enc=$(printf %s "$font" | sed 's/ /%20/g')
    start=0
    while [ $start -le 65280 ]; do
        range="$start-$((start + 255))"
        [ -s "$DIR/fonts/$font/$range.pbf" ] || curl -sfS -o "$DIR/fonts/$font/$range.pbf" "$OFM/fonts/$enc/$range.pbf" || true
        start=$((start + 256))
    done
done

for f in ofm.json ofm.png ofm@2x.json ofm@2x.png; do
    curl -sfS -o "$DIR/sprites/$f" "$OFM/sprites/ofm_f384/$f"
done

# Greece from Geofabrik, OpenMapTiles profile, written next to the old file and swapped in at the end.
docker run --rm -e JAVA_TOOL_OPTIONS="-Xmx3g" -v "$DIR/data:/data" "$PLANETILER" \
    --download --area=greece --output=/data/greece.new.mbtiles --force
mv "$DIR/data/greece.new.mbtiles" "$DIR/data/greece.mbtiles"
