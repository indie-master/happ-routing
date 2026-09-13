#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V2DAT="${V2DAT:-v2dat}"

for file in geoip.dat geosite.dat geoip.dat.sha256 geosite.dat.sha256 manifest.json; do
  test -s "$ROOT/release/$file"
done
for file in \
  DEFAULT.JSON DEFAULT.DEEPLINK \
  CANARY.JSON CANARY.DEEPLINK \
  LEGACY.JSON LEGACY.DEEPLINK; do
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
  -f private -f swiftless-ru -f swiftless-ru-whitelist -f swiftless-wechat \
  "$ROOT/release/geoip.dat"

"$V2DAT" unpack geosite -o "$tmp/geosite" \
  -f private -f category-ru -f swiftless-ru-extra -f swiftless-ru \
  -f whitelist -f category-geoblock-ru -f microsoft -f apple \
  -f epicgames -f riot -f escapefromtarkov -f steam -f twitch \
  -f pinterest -f faceit -f swiftless-google-direct \
  -f swiftless-google-ads -f swiftless-wechat -f google-play \
  -f github -f twitch-ads -f youtube -f telegram -f win-spy \
  -f torrent -f category-ads \
  "$ROOT/release/geosite.dat"

assert_min_lines() {
  local file="$1"
  local minimum="$2"
  local count
  count="$(wc -l < "$file")"
  if (( count < minimum )); then
    echo "$file contains $count rules; expected at least $minimum" >&2
    exit 1
  fi
}

assert_min_lines "$tmp/geoip/geoip_swiftless-ru.txt" 30000
assert_min_lines "$tmp/geoip/geoip_swiftless-ru-whitelist.txt" 5000
assert_min_lines "$tmp/geoip/geoip_swiftless-wechat.txt" 200
assert_min_lines "$tmp/geosite/geosite_category-ru.txt" 500
assert_min_lines "$tmp/geosite/geosite_swiftless-ru-extra.txt" 30
assert_min_lines "$tmp/geosite/geosite_swiftless-ru.txt" 1000
assert_min_lines "$tmp/geosite/geosite_category-geoblock-ru.txt" 500
assert_min_lines "$tmp/geosite/geosite_swiftless-wechat.txt" 30
assert_min_lines "$tmp/geosite/geosite_swiftless-google-direct.txt" 500
assert_min_lines "$tmp/geosite/geosite_swiftless-google-ads.txt" 20

grep -Rqs '101\.32\.104\.0/24' "$tmp/geoip"
grep -Rqs '2408:80f1:21::/48' "$tmp/geoip"
grep -Rqs '5\.8\.43\.' "$tmp/geoip"
grep -Fxqs 'ru' "$tmp/geosite/geosite_category-ru.txt"
grep -Fxqs 'xn--p1ai' "$tmp/geosite/geosite_category-ru.txt"
grep -Rqis 'ipify\.org' "$tmp/geosite"
grep -Rqis 'wechat\.com' "$tmp/geosite"
grep -Rqis 'google\.com' "$tmp/geosite"
grep -Rqis 'doubleclick\.net' "$tmp/geosite"

(
  cd "$ROOT"
  python3 -m unittest discover -s tests -v
)
