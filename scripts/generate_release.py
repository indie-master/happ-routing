#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRECT_SITES = {"geosite:google-direct", "geosite:wechat"}
REQUIRED_PROXY_SITES = {"geosite:google-ads", "geosite:google-play", "geosite:youtube"}
REQUIRED_DIRECT_IPS = {"geoip:private", "geoip:direct", "geoip:wechat"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_template(profile: dict) -> None:
    if profile.get("RouteOrder") != "block-proxy-direct":
        raise ValueError("RouteOrder must be block-proxy-direct")
    if profile.get("DomainStrategy") != "IPIfNonMatch":
        raise ValueError("DomainStrategy must be IPIfNonMatch")
    if profile.get("FakeDNS") != "false":
        raise ValueError("FakeDNS must stay false during the safe rollout")

    direct_sites = set(profile.get("DirectSites", []))
    proxy_sites = set(profile.get("ProxySites", []))
    direct_ips = set(profile.get("DirectIp", []))
    if not REQUIRED_DIRECT_SITES <= direct_sites:
        raise ValueError("DirectSites is missing Google Direct or WeChat")
    if not REQUIRED_PROXY_SITES <= proxy_sites:
        raise ValueError("Google Ads, YouTube and Google Play must remain in ProxySites")
    if not REQUIRED_DIRECT_IPS <= direct_ips:
        raise ValueError("DirectIp is missing required tags")
    if "geosite:google" in direct_sites or "geoip:google" in direct_ips:
        raise ValueError("Broad Google tags are forbidden in DIRECT")

    for key in ("RemoteDNSIP", "DomesticDNSIP"):
        ipaddress.ip_address(profile[key])
    for key in ("RemoteDNSDomain", "DomesticDNSDomain"):
        parsed = urlparse(profile[key])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"{key} must be a valid HTTPS URL")

    for key in ("DirectSites", "DirectIp", "ProxySites", "ProxyIp", "BlockSites", "BlockIp"):
        values = profile.get(key, [])
        if len(values) != len(set(values)):
            raise ValueError(f"{key} contains duplicates")


def write_profile(profile: dict, output_name: str, output_dir: Path) -> None:
    pretty = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    compact = json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
    encoded = base64.b64encode(compact.encode("utf-8")).decode("ascii")
    (output_dir / f"{output_name}.JSON").write_text(pretty, encoding="utf-8")
    (output_dir / f"{output_name}.DEEPLINK").write_text(
        f"happ://routing/add/{encoded}\n", encoding="utf-8"
    )


def generate_profiles(repo: str, tag: str, timestamp: int, template: Path, output_dir: Path) -> None:
    profile = json.loads(template.read_text(encoding="utf-8"))
    validate_template(profile)
    base_url = f"https://cdn.jsdelivr.net/gh/{repo}@{tag}/release"
    profile["Geoipurl"] = f"{base_url}/geoip.dat"
    profile["Geositeurl"] = f"{base_url}/geosite.dat"
    profile["LastUpdated"] = str(timestamp)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_profile(profile, "DEFAULT", output_dir)

    canary = json.loads(json.dumps(profile))
    canary["Name"] = f"{profile['Name']}-canary"
    write_profile(canary, "CANARY", output_dir)


def write_release_metadata(release_dir: Path, tag: str, timestamp: int, sources: dict[str, str]) -> None:
    files = {}
    for name in ("geoip.dat", "geosite.dat"):
        path = release_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing release artifact: {path}")
        digest = sha256(path)
        files[name] = {"sha256": digest, "size": path.stat().st_size}
        (release_dir / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="ascii")

    manifest = {
        "tag": tag,
        "lastUpdated": str(timestamp),
        "sources": sources,
        "files": files,
    }
    (release_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate immutable Happ routing profiles")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--timestamp", required=True, type=int)
    parser.add_argument("--template", type=Path, default=ROOT / "config/happ.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "HAPP")
    parser.add_argument("--profiles-only", action="store_true")
    parser.add_argument("--v2fly-sha", default="unknown")
    parser.add_argument("--roscom-geosite-sha", default="unknown")
    parser.add_argument("--roscom-geoip-sha", default="unknown")
    parser.add_argument("--geoip-builder-sha", default="unknown")
    args = parser.parse_args()

    generate_profiles(args.repo, args.tag, args.timestamp, args.template, args.output_dir)
    if not args.profiles_only:
        write_release_metadata(
            ROOT / "release",
            args.tag,
            args.timestamp,
            {
                "v2fly/domain-list-community": args.v2fly_sha,
                "hydraponique/roscomvpn-geosite": args.roscom_geosite_sha,
                "hydraponique/roscomvpn-geoip": args.roscom_geoip_sha,
                "Loyalsoldier/geoip": args.geoip_builder_sha,
            },
        )


if __name__ == "__main__":
    main()
