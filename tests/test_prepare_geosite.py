import tempfile
import unittest
from pathlib import Path

from scripts.prepare_geosite import prepare_geosite_sources


class PrepareGeositeTests(unittest.TestCase):
    def test_roscom_category_does_not_replace_community_category(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            community = root / "community"
            roscom = root / "roscom"
            custom = root / "custom"
            output = root / "output"
            community.mkdir()
            roscom.mkdir()
            custom.mkdir()

            (community / "category-ru").write_text("include:tld-ru\n")
            (community / "tld-ru").write_text("ru\n")
            (roscom / "category-ru").write_text("domain:ipify.org\n")
            (roscom / "whitelist").write_text("domain:gosuslugi.ru\n")
            (roscom / "category-geoblock-ru").write_text("domain:4pda.ru\n")
            (custom / "swiftless-ru").write_text(
                "include:category-ru\ninclude:swiftless-ru-extra\n"
            )

            prepare_geosite_sources(community, roscom, custom, output)

            self.assertEqual(
                (output / "category-ru").read_text(), "include:tld-ru\n"
            )
            self.assertEqual(
                (output / "swiftless-ru-extra").read_text(),
                "domain:ipify.org\n",
            )
            self.assertTrue((output / "category-geoblock-ru").is_file())


if __name__ == "__main__":
    unittest.main()
