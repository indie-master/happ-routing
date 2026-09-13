#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path


DOMAIN_EXACT_TYPES = {"DOMAIN", "HOST"}
DOMAIN_SUFFIX_TYPES = {"DOMAIN-SUFFIX", "HOST-SUFFIX"}
IP_TYPES = {"IP-CIDR", "IP-CIDR6"}
IPV4_PREFIX_RE = re.compile(r"(?:[0-9]{1,3}\.){3}")


def source_lines(path: Path):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Required WeChat source is missing or empty: {path}")
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if line:
            yield number, line


def normalize_hostname(value: str, path: Path, number: int) -> str:
    hostname = value.strip().lower().rstrip(".")
    if not hostname or " " in hostname or "." not in hostname:
        raise ValueError(f"Invalid hostname at {path}:{number}: {value!r}")
    return hostname


def read_upstream_domains(path: Path) -> set[str]:
    domains: set[str] = set()
    for number, line in source_lines(path):
        parts = [part.strip() for part in line.split(",")]
        rule_type = parts[0].upper()
        if rule_type not in DOMAIN_EXACT_TYPES | DOMAIN_SUFFIX_TYPES:
            continue
        if len(parts) < 2:
            raise ValueError(f"Malformed domain rule at {path}:{number}")
        hostname = normalize_hostname(parts[1], path, number)
        if rule_type in DOMAIN_EXACT_TYPES:
            domains.add(f"full:{hostname}")
        else:
            domains.add(hostname)
    if not domains:
        raise ValueError(f"No supported WeChat domain rules found in {path}")
    return domains


def read_extra_domains(path: Path) -> set[str]:
    domains: set[str] = set()
    for number, line in source_lines(path):
        normalized = line.lower()
        if normalized.startswith("include:"):
            raise ValueError(f"Includes are not allowed at {path}:{number}")
        domains.add(normalized)
    return domains


def read_upstream_networks(path: Path) -> set[ipaddress._BaseNetwork]:
    networks: set[ipaddress._BaseNetwork] = set()
    for number, line in source_lines(path):
        parts = [part.strip() for part in line.split(",")]
        rule_type = parts[0].upper()
        if len(parts) < 2:
            continue
        value = parts[1]
        if rule_type in IP_TYPES:
            try:
                networks.add(ipaddress.ip_network(value, strict=False))
            except ValueError as exc:
                raise ValueError(f"Invalid network at {path}:{number}: {value}") from exc
        elif rule_type == "DOMAIN-KEYWORD" and IPV4_PREFIX_RE.fullmatch(value):
            # The maintained Surge list represents known WeChat IPv4 /24s as
            # IP-looking DOMAIN-KEYWORD entries. Convert only this exact form;
            # ordinary domain keywords are deliberately ignored.
            try:
                networks.add(ipaddress.ip_network(f"{value}0/24"))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid IPv4 prefix at {path}:{number}: {value}"
                ) from exc
    if not networks:
        raise ValueError(f"No supported WeChat IP rules found in {path}")
    return networks


def read_extra_networks(path: Path) -> set[ipaddress._BaseNetwork]:
    networks: set[ipaddress._BaseNetwork] = set()
    for number, line in source_lines(path):
        try:
            networks.add(ipaddress.ip_network(line, strict=False))
        except ValueError as exc:
            raise ValueError(f"Invalid network at {path}:{number}: {line}") from exc
    return networks


def network_sort_key(network: ipaddress._BaseNetwork) -> tuple[int, int, int]:
    return network.version, int(network.network_address), network.prefixlen


def write_domains(path: Path, domains: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# Generated from blackmatrix7 WeChat rules plus local additions.",
        "# Do not edit this build artifact; edit custom/wechat/domains.txt.",
        *sorted(domains),
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")


def write_networks(path: Path, networks: set[ipaddress._BaseNetwork]) -> None:
    collapsed: list[ipaddress._BaseNetwork] = []
    for version in (4, 6):
        selected = [network for network in networks if network.version == version]
        collapsed.extend(ipaddress.collapse_addresses(selected))
    collapsed.sort(key=network_sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "# Generated from blackmatrix7 WeChat rules plus local additions.",
        "# AS132203 is intentionally not expanded: it includes unrelated Tencent Cloud.",
        *(str(network) for network in collapsed),
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")


def generate(
    domain_source: Path,
    ip_source: Path,
    domain_extra: Path,
    ip_extra: Path,
    domain_output: Path,
    ip_output: Path,
) -> tuple[int, int]:
    domains = read_upstream_domains(domain_source) | read_extra_domains(domain_extra)
    networks = read_upstream_networks(ip_source) | read_extra_networks(ip_extra)
    write_domains(domain_output, domains)
    write_networks(ip_output, networks)
    return len(domains), len(networks)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate maintained Swiftless WeChat domain and IP categories"
    )
    parser.add_argument("--domain-source", required=True, type=Path)
    parser.add_argument("--ip-source", required=True, type=Path)
    parser.add_argument("--domain-extra", required=True, type=Path)
    parser.add_argument("--ip-extra", required=True, type=Path)
    parser.add_argument("--domain-output", required=True, type=Path)
    parser.add_argument("--ip-output", required=True, type=Path)
    args = parser.parse_args()
    domain_count, network_count = generate(
        args.domain_source,
        args.ip_source,
        args.domain_extra,
        args.ip_extra,
        args.domain_output,
        args.ip_output,
    )
    print(
        f"Generated {domain_count} WeChat domain rules and "
        f"{network_count} uncollapsed IP rules"
    )


if __name__ == "__main__":
    main()
