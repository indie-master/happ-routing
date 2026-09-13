#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


RESERVED_CUSTOM_NAMES = {"category-ru", "swiftless-ru-extra"}


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Required geosite source is missing or empty: {path}")


def copy_contents(source: Path, destination: Path) -> None:
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def prepare_geosite_sources(
    community_data: Path,
    roscom_data: Path,
    custom_data: Path,
    output: Path,
) -> None:
    for path in (community_data, roscom_data, custom_data):
        if not path.is_dir():
            raise ValueError(f"Required geosite directory is missing: {path}")

    community_ru = community_data / "category-ru"
    roscom_ru = roscom_data / "category-ru"
    require_file(community_ru)
    require_file(roscom_ru)
    require_file(roscom_data / "whitelist")
    require_file(roscom_data / "category-geoblock-ru")

    collisions = sorted(
        name for name in RESERVED_CUSTOM_NAMES if (custom_data / name).exists()
    )
    if collisions:
        raise ValueError(
            "Custom geosite data uses reserved names: " + ", ".join(collisions)
        )

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    # RoscomVPN intentionally ships a much smaller file also named
    # category-ru. Keep it as an additional category instead of silently
    # replacing v2fly's broad community category (which includes all RU TLDs).
    copy_contents(community_data, output)
    copy_contents(roscom_data, output)
    shutil.copy2(roscom_ru, output / "swiftless-ru-extra")
    shutil.copy2(community_ru, output / "category-ru")
    copy_contents(custom_data, output)

    require_file(output / "category-ru")
    require_file(output / "swiftless-ru-extra")
    require_file(output / "swiftless-ru")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge community, RoscomVPN and Swiftless geosite sources safely"
    )
    parser.add_argument("--community-data", required=True, type=Path)
    parser.add_argument("--roscom-data", required=True, type=Path)
    parser.add_argument("--custom-data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    prepare_geosite_sources(
        args.community_data,
        args.roscom_data,
        args.custom_data,
        args.output,
    )


if __name__ == "__main__":
    main()
