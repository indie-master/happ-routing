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
        self.assertIn("geosite:google-ads", profile["ProxySites"])
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
            prefix = "happ://routing/add/"
            self.assertTrue(deeplink.startswith(prefix))
            decoded = json.loads(base64.b64decode(deeplink[len(prefix) :]))
            self.assertEqual(decoded["Name"], "RoscomVPN")
            self.assertEqual(decoded["LastUpdated"], "1788393600")
            self.assertIn("geosite:google-direct", decoded["DirectSites"])
            self.assertIn("geosite:google-ads", decoded["ProxySites"])
            self.assertIn("geosite:youtube", decoded["ProxySites"])
            self.assertTrue(decoded["Geoipurl"].endswith("/release/geoip.dat"))

            canary = json.loads((output / "CANARY.JSON").read_text())
            self.assertEqual(canary["Name"], "RoscomVPN-canary")


if __name__ == "__main__":
    unittest.main()
