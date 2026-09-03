#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V2DAT="${V2DAT:-v2dat}"

for file in geoip.dat geosite.dat geoip.dat.sha256 geosite.dat.sha256 manifest.json; do
  test -s "$ROOT/release/$file"
done
for file in DEFAULT.JSON DEFAULT.DEEPLINK CANARY.JSON CANARY.DEEPLINK; do
  test -s "$ROOT/HAPP/$file"
done

(
  cd "$ROOT/release"
  sha256sum -c geoip.dat.sha256
  sha256sum -c geosite.dat.sha256
)

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/geoip" "$tmp/geosite"

"$V2DAT" unpack geoip -o "$tmp/geoip" \
  -f direct -f private -f whitelist -f wechat \
  "$ROOT/release/geoip.dat"

"$V2DAT" unpack geosite -o "$tmp/geosite" \
  -f private -f category-ru -f whitelist -f microsoft -f apple \
  -f epicgames -f riot -f escapefromtarkov -f steam -f twitch \
  -f pinterest -f faceit -f google-direct -f google-ads -f wechat -f google-play \
  -f github -f twitch-ads -f youtube -f telegram -f win-spy \
  -f torrent -f category-ads \
  "$ROOT/release/geosite.dat"

rg -q '101\.32\.104\.4/32' "$tmp/geoip"
rg -qi 'wechat\.com' "$tmp/geosite"
rg -qi 'google\.com' "$tmp/geosite"
rg -qi 'doubleclick\.net' "$tmp/geosite"

(
  cd "$ROOT"
  python3 -m unittest discover -s tests -v
)
