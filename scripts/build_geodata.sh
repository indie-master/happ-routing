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
BLACKMATRIX_DIR="${BLACKMATRIX_DIR:-$UPSTREAM_DIR/ios-rule-script}"

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

for dir in \
  "$V2FLY_DIR" \
  "$ROSCOM_GEOSITE_DIR" \
  "$ROSCOM_GEOIP_DIR" \
  "$GEOIP_BUILDER_DIR" \
  "$BLACKMATRIX_DIR"; do
  require_dir "$dir"
done

for file in direct private whitelist; do
  require_file "$ROSCOM_GEOIP_DIR/release/text/$file.txt"
done
require_file "$BLACKMATRIX_DIR/rule/QuantumultX/WeChat/WeChat.list"
require_file "$BLACKMATRIX_DIR/rule/Surge/WeChat/WeChat_Resolve.list"
require_file "$ROOT/custom/wechat/domains.txt"
require_file "$ROOT/custom/wechat/ips.txt"

rm -rf "$BUILD_DIR/geosite-data" "$BUILD_DIR/geosite-output"
mkdir -p "$BUILD_DIR/geosite-data" "$BUILD_DIR/geosite-output" "$OUTPUT_DIR"

# Preserve v2fly's broad category-ru and add RoscomVPN's smaller category under
# a different name. A blind overlay used to replace the community category.
python3 "$ROOT/scripts/prepare_geosite.py" \
  --community-data "$V2FLY_DIR/data" \
  --roscom-data "$ROSCOM_GEOSITE_DIR/data" \
  --custom-data "$ROOT/custom/geosite" \
  --output "$BUILD_DIR/geosite-data"

# Refresh WeChat domains and IP ranges from a focused maintained source
# and merge the local production additions kept in this repository.
python3 "$ROOT/scripts/generate_wechat_rules.py" \
  --domain-source "$BLACKMATRIX_DIR/rule/QuantumultX/WeChat/WeChat.list" \
  --ip-source "$BLACKMATRIX_DIR/rule/Surge/WeChat/WeChat_Resolve.list" \
  --domain-extra "$ROOT/custom/wechat/domains.txt" \
  --ip-extra "$ROOT/custom/wechat/ips.txt" \
  --domain-output "$BUILD_DIR/geosite-data/swiftless-wechat" \
  --ip-output "$BUILD_DIR/swiftless-wechat.txt"

go -C "$V2FLY_DIR" run ./ \
  --datapath="$BUILD_DIR/geosite-data" \
  --outputdir="$BUILD_DIR/geosite-output"

require_file "$BUILD_DIR/geosite-output/dlc.dat"
install -m 0644 "$BUILD_DIR/geosite-output/dlc.dat" "$OUTPUT_DIR/geosite.dat"

# Rebuild GeoIP from RoscomVPN's already filtered text exports and append a
# separate WeChat tag. The profile uses Swiftless-owned category names and
# deliberately avoids placing all Tencent Cloud networks into DIRECT.
rm -rf "$GEOIP_BUILDER_DIR/output-custom"
install -m 0644 "$ROSCOM_GEOIP_DIR/release/text/direct.txt" "$GEOIP_BUILDER_DIR/swiftless-ru.txt"
install -m 0644 "$ROSCOM_GEOIP_DIR/release/text/private.txt" "$GEOIP_BUILDER_DIR/private.txt"
install -m 0644 "$ROSCOM_GEOIP_DIR/release/text/whitelist.txt" "$GEOIP_BUILDER_DIR/swiftless-ru-whitelist.txt"
install -m 0644 "$BUILD_DIR/swiftless-wechat.txt" "$GEOIP_BUILDER_DIR/swiftless-wechat.txt"
install -m 0644 "$ROOT/config/geoip.json" "$GEOIP_BUILDER_DIR/config.custom.json"

go -C "$GEOIP_BUILDER_DIR" run ./ convert -c config.custom.json

require_file "$GEOIP_BUILDER_DIR/output-custom/geoip.dat"
install -m 0644 "$GEOIP_BUILDER_DIR/output-custom/geoip.dat" "$OUTPUT_DIR/geoip.dat"

echo "Built $OUTPUT_DIR/geosite.dat and $OUTPUT_DIR/geoip.dat"
