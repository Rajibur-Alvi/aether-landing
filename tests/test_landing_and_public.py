from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LandingCtaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text()

    def test_paid_plan_ctas_use_checkout_not_scanner_modal(self):
        self.assertNotIn("openModal('signal')", self.html)
        self.assertNotIn("openModal('signal_pro')", self.html)
        self.assertIn("subscribe('signal', event)", self.html)
        self.assertIn("subscribe('signal_pro', event)", self.html)

    def test_account_ctas_go_to_dashboard(self):
        self.assertIn("function goDashboard()", self.html)
        self.assertGreaterEqual(self.html.count("goDashboard()"), 3)

    def test_enterprise_demo_ctas_do_not_open_scanner_modal(self):
        self.assertNotIn("openModal('aether_core')", self.html)
        self.assertIn("function requestDemo()", self.html)
        self.assertIn("requestDemo()", self.html)

    def test_public_chat_request_uses_free_trial_token_limit(self):
        self.assertIn("max_tokens: 512", self.html)


class PublicFreeScanTest(unittest.TestCase):
    def test_public_ingest_does_not_write_auth_user_metadata(self):
        source = (ROOT / "backend" / "routers" / "public.py").read_text()
        self.assertNotIn("Metadata storage failed", source)
        self.assertNotIn('sb.table("documents").upsert', source)

    def test_public_chat_caps_tokens_instead_of_rejecting_schema_default(self):
        source = (ROOT / "backend" / "routers" / "public.py").read_text()
        self.assertNotIn("Max tokens limited to 512 for free trial.", source)
        self.assertGreaterEqual(source.count("max_tokens = min(request.max_tokens or 512, 512)"), 2)


if __name__ == "__main__":
    unittest.main()
