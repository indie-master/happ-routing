import base64
import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_release import generate_profiles, validate_template


ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_template_invariants(self):
        profile = json.loads((ROOT / "config/happ.json").read_text(encoding="utf-8"))
        validate_template(profile)
        self.assertEqual(profile["Name"], "swiftless-routing")
        self.assertEqual(profile["DomesticDNSType"], "DoU")
        self.assertEqual(profile["DomesticDNSDomain"], "")
        self.assertIn("geosite:swiftless-ru", profile["DirectSites"])
        self.assertIn("geoip:swiftless-ru-whitelist", profile["DirectIp"])
        self.assertIn("geosite:swiftless-google-ads", profile["ProxySites"])
        self.assertIn("geosite:category-geoblock-ru", profile["ProxySites"])
        self.assertIn("geosite:youtube", profile["ProxySites"])
        self.assertNotIn("geosite:tencent", profile["DirectSites"])

    def test_generated_deeplink_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generate_profiles(
                "indie-master/happ-routing",
                "20260903000000",
                1788393600,
                ROOT / "config/happ.json",
                output,
            )
            deeplink = (output / "DEFAULT.DEEPLINK").read_text().strip()
            prefix = "happ://routing/onadd/"
            self.assertTrue(deeplink.startswith(prefix))
            decoded = json.loads(base64.b64decode(deeplink[len(prefix) :]))
            self.assertEqual(decoded["Name"], "swiftless-routing")
            self.assertEqual(decoded["LastUpdated"], "1788393600")
            self.assertIn("geosite:swiftless-google-direct", decoded["DirectSites"])
            self.assertIn("geosite:swiftless-google-ads", decoded["ProxySites"])
            self.assertIn("geosite:youtube", decoded["ProxySites"])
            self.assertTrue(decoded["Geoipurl"].endswith("/release/geoip.dat"))

            canary = json.loads((output / "CANARY.JSON").read_text())
            self.assertEqual(canary["Name"], "swiftless-routing-canary")

            legacy = json.loads((output / "LEGACY.JSON").read_text())
            self.assertEqual(legacy["Name"], "RoscomVPN")
            self.assertEqual(legacy["Geoipurl"], decoded["Geoipurl"])


if __name__ == "__main__":
    unittest.main()
