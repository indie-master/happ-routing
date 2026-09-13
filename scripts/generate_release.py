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
PROFILE_NAME = "swiftless-routing"
LEGACY_PROFILE_NAME = "RoscomVPN"
REQUIRED_DIRECT_SITES = {
    "geosite:swiftless-ru",
    "geosite:swiftless-google-direct",
    "geosite:swiftless-wechat",
}
REQUIRED_PROXY_SITES = {
    "geosite:swiftless-google-ads",
    "geosite:category-geoblock-ru",
    "geosite:google-play",
    "geosite:youtube",
}
REQUIRED_DIRECT_IPS = {
    "geoip:private",
    "geoip:swiftless-ru",
    "geoip:swiftless-ru-whitelist",
    "geoip:swiftless-wechat",
}
FORBIDDEN_DIRECT_TAGS = {
    "geosite:google",
    "geosite:tencent",
    "geoip:google",
    "geoip:tencent",
    "geoip:cn",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dns_endpoint(profile: dict, prefix: str) -> None:
    dns_type = profile.get(f"{prefix}DNSType")
    dns_domain = profile.get(f"{prefix}DNSDomain")
    dns_ip = str(profile.get(f"{prefix}DNSIP", ""))
    ipaddress.ip_address(dns_ip)

    if dns_type == "DoH":
        parsed = urlparse(str(dns_domain))
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"{prefix}DNSDomain must be a valid HTTPS URL for DoH")
        hosts = profile.get("DnsHosts")
        if not isinstance(hosts, dict) or hosts.get(parsed.hostname) != dns_ip:
            raise ValueError(
                f"DnsHosts must bootstrap {parsed.hostname} to {dns_ip}"
            )
    elif dns_type == "DoU":
        if dns_domain not in {"", None}:
            raise ValueError(f"{prefix}DNSDomain must be empty for DoU")
    else:
        raise ValueError(f"Unsupported {prefix}DNSType: {dns_type!r}")


def validate_template(profile: dict) -> None:
    if profile.get("Name") != PROFILE_NAME:
        raise ValueError(f"Profile Name must be {PROFILE_NAME!r}")
    if profile.get("GlobalProxy") != "true":
        raise ValueError("GlobalProxy must stay true")
    if profile.get("RouteOrder") != "block-proxy-direct":
        raise ValueError("RouteOrder must be block-proxy-direct")
    if profile.get("DomainStrategy") != "IPIfNonMatch":
        raise ValueError("DomainStrategy must be IPIfNonMatch")
    if profile.get("FakeDNS") != "false":
        raise ValueError("FakeDNS must stay false during the safe rollout")
    if profile.get("UseChunkFiles") != "true":
        raise ValueError("UseChunkFiles must stay true")

    direct_sites = set(profile.get("DirectSites", []))
    proxy_sites = set(profile.get("ProxySites", []))
    direct_ips = set(profile.get("DirectIp", []))
    if not REQUIRED_DIRECT_SITES <= direct_sites:
        raise ValueError("DirectSites is missing required Swiftless tags")
    if not REQUIRED_PROXY_SITES <= proxy_sites:
        raise ValueError("ProxySites is missing required exception tags")
    if not REQUIRED_DIRECT_IPS <= direct_ips:
        raise ValueError("DirectIp is missing required tags")
    forbidden = (direct_sites | direct_ips) & FORBIDDEN_DIRECT_TAGS
    if forbidden:
        raise ValueError(f"Over-broad DIRECT tags are forbidden: {sorted(forbidden)}")

    validate_dns_endpoint(profile, "Remote")
    validate_dns_endpoint(profile, "Domestic")

    for key in ("DirectSites", "DirectIp", "ProxySites", "ProxyIp", "BlockSites", "BlockIp"):
        values = profile.get(key, [])
        if len(values) != len(set(values)):
            raise ValueError(f"{key} contains duplicates")


def write_profile(
    profile: dict,
    output_name: str,
    output_dir: Path,
    action: str = "add",
) -> None:
    if action not in {"add", "onadd"}:
        raise ValueError(f"Unsupported Happ routing action: {action}")
    pretty = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    compact = json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
    encoded = base64.b64encode(compact.encode("utf-8")).decode("ascii")
    (output_dir / f"{output_name}.JSON").write_text(pretty, encoding="utf-8")
    (output_dir / f"{output_name}.DEEPLINK").write_text(
        f"happ://routing/{action}/{encoded}\n", encoding="utf-8"
    )


def generate_profiles(
    repo: str,
    tag: str,
    timestamp: int,
    template: Path,
    output_dir: Path,
) -> None:
    profile = json.loads(template.read_text(encoding="utf-8"))
    validate_template(profile)
    base_url = f"https://cdn.jsdelivr.net/gh/{repo}@{tag}/release"
    profile["Geoipurl"] = f"{base_url}/geoip.dat"
    profile["Geositeurl"] = f"{base_url}/geosite.dat"
    profile["LastUpdated"] = str(timestamp)
    output_dir.mkdir(parents=True, exist_ok=True)
    # onadd is intentional for the one-time RoscomVPN -> swiftless-routing
    # rename: Happ only overwrites profiles with the same name. It also makes
    # the new provider-managed profile active after the geodata swap succeeds.
    write_profile(profile, "DEFAULT", output_dir, action="onadd")

    canary = json.loads(json.dumps(profile))
    canary["Name"] = f"{profile['Name']}-canary"
    write_profile(canary, "CANARY", output_dir)

    # Retain an atomic-update path under the old identity for rollback during
    # migration. New installations and the updater use DEFAULT.
    legacy = json.loads(json.dumps(profile))
    legacy["Name"] = LEGACY_PROFILE_NAME
    write_profile(legacy, "LEGACY", output_dir)


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
    parser.add_argument("--wechat-rules-sha", default="unknown")
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
                "blackmatrix7/ios_rule_script": args.wechat_rules_sha,
            },
        )


if __name__ == "__main__":
    main()
