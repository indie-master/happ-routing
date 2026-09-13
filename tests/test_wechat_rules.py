import tempfile
import unittest
from pathlib import Path

from scripts.generate_wechat_rules import generate


class WeChatRuleTests(unittest.TestCase):
    def test_quantumult_and_surge_rules_are_converted_and_merged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            domain_source = root / "domains.list"
            ip_source = root / "ips.list"
            domain_extra = root / "domain-extra"
            ip_extra = root / "ip-extra"
            domain_output = root / "swiftless-wechat"
            ip_output = root / "swiftless-wechat.txt"

            domain_source.write_text(
                "HOST,dl.wechat.com,WeChat\n"
                "HOST-SUFFIX,weixin.qq.com,WeChat\n"
                "IP-ASN,132203,WeChat\n",
                encoding="utf-8",
            )
            ip_source.write_text(
                "DOMAIN-KEYWORD,101.32.104.\n"
                "IP-CIDR,111.30.160.0/20,no-resolve\n"
                "IP-CIDR6,2408:80f1:21::/48,no-resolve\n"
                "IP-ASN,132203,no-resolve\n",
                encoding="utf-8",
            )
            domain_extra.write_text("wechatpay.cn\n", encoding="utf-8")
            ip_extra.write_text("129.226.3.47/32\n", encoding="utf-8")

            domain_count, network_count = generate(
                domain_source,
                ip_source,
                domain_extra,
                ip_extra,
                domain_output,
                ip_output,
            )

            domains = domain_output.read_text(encoding="utf-8")
            networks = ip_output.read_text(encoding="utf-8")
            self.assertEqual(domain_count, 3)
            self.assertEqual(network_count, 4)
            self.assertIn("full:dl.wechat.com", domains)
            self.assertIn("weixin.qq.com", domains)
            self.assertIn("wechatpay.cn", domains)
            self.assertIn("101.32.104.0/24", networks)
            self.assertIn("111.30.160.0/20", networks)
            self.assertIn("2408:80f1:21::/48", networks)
            self.assertFalse(
                any(line.strip() == "132203" for line in networks.splitlines())
            )


if __name__ == "__main__":
    unittest.main()
