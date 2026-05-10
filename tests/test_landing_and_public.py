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

    def test_public_upload_picker_accepts_docx(self):
        self.assertIn('accept=".txt,.pdf,.docx"', self.html)

    def test_public_analyzer_is_not_blocked_by_local_storage_usage_count(self):
        self.assertNotIn("aether_free_uses", self.html)
        self.assertNotIn("freeUses >= 2", self.html)
        self.assertNotIn("textInput').disabled = true", self.html)
        self.assertNotIn("fileInput').disabled = true", self.html)
        self.assertNotIn("analyzeBtn').classList.add('hidden')", self.html)

    def test_public_analyzer_is_not_blocked_by_deep_health_probe(self):
        self.assertNotIn('onclick="runAnalysis()" disabled', self.html)
        self.assertNotIn("document.getElementById('analyzeBtn').disabled = !backendReady", self.html)
        self.assertNotIn("Backend is still warming up. Please wait a moment and try again.", self.html)

    def test_heatmap_uses_runtime_grid_columns_instead_of_missing_tailwind_classes(self):
        self.assertNotIn("grid-cols-15", self.html)
        self.assertNotIn("grid-cols-20", self.html)
        self.assertIn("grid.style.gridTemplateColumns", self.html)


class DashboardAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "dashboard.html").read_text()

    def test_missing_auth_session_does_not_call_remote_signout_loop(self):
        self.assertIn("function showAuthOverlay()", self.html)
        self.assertIn("showAuthOverlay();", self.html)
        self.assertNotIn("} else {\n            signOut();\n        }", self.html)

    def test_empty_documents_render_clears_stale_document_cards(self):
        marker = "function renderDocuments()"
        start = self.html.index(marker)
        end = self.html.index("async function deleteDocument", start)
        render_source = self.html[start:end]
        empty_check = render_source.index("if (!documents.length)")
        clear_call = render_source.index("list.innerHTML = '';")
        self.assertLess(clear_call, empty_check)

    def test_dashboard_upload_picker_accepts_docx(self):
        self.assertIn('Supported: .txt, .pdf, and .docx files', self.html)
        self.assertIn('accept=".txt,.pdf,.docx"', self.html)


class PublicFreeScanTest(unittest.TestCase):
    def test_public_ingest_does_not_write_auth_user_metadata(self):
        source = (ROOT / "backend" / "routers" / "public.py").read_text()
        self.assertNotIn("Metadata storage failed", source)
        self.assertNotIn('sb.table("documents").upsert', source)

    def test_public_chat_caps_tokens_instead_of_rejecting_schema_default(self):
        source = (ROOT / "backend" / "routers" / "public.py").read_text()
        self.assertNotIn("Max tokens limited to 512 for free trial.", source)
        self.assertGreaterEqual(source.count("max_tokens = min(request.max_tokens or 512, 512)"), 2)

    def test_public_scan_accepts_larger_trial_payloads(self):
        source = (ROOT / "backend" / "routers" / "public.py").read_text()
        self.assertIn("PUBLIC_TEXT_LIMIT_BYTES = 200 * 1024", source)
        self.assertIn("PUBLIC_FILE_LIMIT_BYTES = 5 * 1024 * 1024", source)
        self.assertIn("Maximum 200KB", source)
        self.assertIn("Maximum 5MB", source)
        self.assertNotIn("50 * 1024", source)
        self.assertNotIn("Maximum 1MB", source)

    def test_public_file_ingest_supports_docx(self):
        source = (ROOT / "backend" / "routers" / "public.py").read_text()
        self.assertIn("extract_text_from_docx_bytes", source)
        self.assertIn('filename.lower().endswith(".docx")', source)
        self.assertIn('SUPPORTED_FILE_TYPES = ".txt, .pdf, .docx"', source)
        self.assertIn("Supported: {SUPPORTED_FILE_TYPES}", source)

    def test_authenticated_file_ingest_supports_docx(self):
        source = (ROOT / "backend" / "routers" / "ingest.py").read_text()
        self.assertIn("extract_text_from_docx_bytes", source)
        self.assertIn('filename.lower().endswith(".docx")', source)
        self.assertIn("Supported: .txt, .pdf, .docx", source)


class BackendAuthTest(unittest.TestCase):
    def test_auth_middleware_supports_supabase_es256_jwks_tokens(self):
        source = (ROOT / "backend" / "middleware" / "auth.py").read_text()
        self.assertIn("jwt.get_unverified_header", source)
        self.assertIn(".well-known/jwks.json", source)
        self.assertIn('"ES256"', source)
        self.assertNotIn('algorithms=["HS256"]', source)


class DeploymentConfigTest(unittest.TestCase):
    def test_render_env_vars_are_unique_and_target_live_service(self):
        source = (ROOT / "backend" / "render.yaml").read_text()
        self.assertIn("name: aether-landing", source)
        self.assertEqual(source.count("key: SUPABASE_JWT_SECRET"), 1)

    def test_frontend_library_defaults_to_live_render_backend(self):
        source = (ROOT / "frontend-lib" / "api.ts").read_text()
        self.assertIn('https://aether-landing.onrender.com', source)
        self.assertNotIn('https://entropy-backend.onrender.com', source)

    def test_pinecone_setup_uses_hosted_embedding_dimension(self):
        deploy = (ROOT / "DEPLOY.md").read_text()
        create_index = (ROOT / "backend" / "create_index.py").read_text()

        self.assertIn("Dimension: **768**", deploy)
        self.assertIn("dim=768", deploy)
        self.assertNotIn("Dimension: **384**", deploy)
        self.assertNotIn("dim=384", deploy)
        self.assertIn("dimension=settings.pinecone_dimension", create_index)


if __name__ == "__main__":
    unittest.main()
