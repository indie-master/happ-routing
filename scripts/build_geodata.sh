#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_DIR="${UPSTREAM_DIR:-$ROOT/.upstream}"
BUILD_DIR="${BUILD_DIR:-$ROOT/.build}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/release}"

V2FLY_DIR="${V2FLY_DIR:-$UPSTREAM_DIR/domain-list-community}"
ROSCOM_GEOSITE_DIR="${ROSCOM_GEOSITE_DIR:-$UPSTREAM_DIR/roscomvpn-geosite}"
ROSCOM_GEOIP_DIR="${ROSCOM_GEOIP_DIR:-$UPSTREAM_DIR/roscomvpn-geoip}"
GEOIP_BUILDER_DIR="${GEOIP_BUILDER_DIR:-$UPSTREAM_DIR/geoip-builder}"

require_dir() {
  if [[ ! -d "$1" ]]; then
    echo "Required source directory is missing: $1" >&2
    exit 1
  fi
}

require_file() {
  if [[ ! -s "$1" ]]; then
    echo "Required source file is missing or empty: $1" >&2
    exit 1
  fi
}

for dir in "$V2FLY_DIR" "$ROSCOM_GEOSITE_DIR" "$ROSCOM_GEOIP_DIR" "$GEOIP_BUILDER_DIR"; do
  require_dir "$dir"
done

for file in direct private whitelist; do
  require_file "$ROSCOM_GEOIP_DIR/release/text/$file.txt"
done
require_file "$ROOT/custom/geoip/wechat.txt"

rm -rf "$BUILD_DIR/geosite-data" "$BUILD_DIR/geosite-output"
mkdir -p "$BUILD_DIR/geosite-data" "$BUILD_DIR/geosite-output" "$OUTPUT_DIR"

# Start with the complete current community database, overlay RoscomVPN's
# curated categories, then apply this repository's small local additions.
cp -a "$V2FLY_DIR/data/." "$BUILD_DIR/geosite-data/"
cp -a "$ROSCOM_GEOSITE_DIR/data/." "$BUILD_DIR/geosite-data/"
cp -a "$ROOT/custom/geosite/." "$BUILD_DIR/geosite-data/"

go -C "$V2FLY_DIR" run ./ \
  --datapath="$BUILD_DIR/geosite-data" \
  --outputdir="$BUILD_DIR/geosite-output"

require_file "$BUILD_DIR/geosite-output/dlc.dat"
install -m 0644 "$BUILD_DIR/geosite-output/dlc.dat" "$OUTPUT_DIR/geosite.dat"

# Rebuild GeoIP from RoscomVPN's already filtered text exports and append a
# separate WeChat tag. This preserves direct/private/whitelist semantics and
# avoids placing all Tencent Cloud networks into DIRECT.
rm -rf "$GEOIP_BUILDER_DIR/output-custom"
install -m 0644 "$ROSCOM_GEOIP_DIR/release/text/direct.txt" "$GEOIP_BUILDER_DIR/direct.txt"
install -m 0644 "$ROSCOM_GEOIP_DIR/release/text/private.txt" "$GEOIP_BUILDER_DIR/private.txt"
install -m 0644 "$ROSCOM_GEOIP_DIR/release/text/whitelist.txt" "$GEOIP_BUILDER_DIR/whitelist.txt"
install -m 0644 "$ROOT/custom/geoip/wechat.txt" "$GEOIP_BUILDER_DIR/wechat.txt"
install -m 0644 "$ROOT/config/geoip.json" "$GEOIP_BUILDER_DIR/config.custom.json"

go -C "$GEOIP_BUILDER_DIR" run ./ convert -c config.custom.json

require_file "$GEOIP_BUILDER_DIR/output-custom/geoip.dat"
install -m 0644 "$GEOIP_BUILDER_DIR/output-custom/geoip.dat" "$OUTPUT_DIR/geoip.dat"

echo "Built $OUTPUT_DIR/geosite.dat and $OUTPUT_DIR/geoip.dat"

