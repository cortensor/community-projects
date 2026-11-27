"""Offline tests for checks.py against a local HTTP server (python -m unittest)."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import checks

GOOD = """<!doctype html><html lang="en"><head><title>Acme Granite | Countertops in Cape Cod</title>
<meta name="description" content="Granite and quartz countertops measured, fabricated and installed on Cape Cod.">
<link rel="canonical" href="https://acme.test/"><link rel="icon" href="/f.ico"><link rel="apple-touch-icon" href="/a.png">
<meta property="og:title" content="Acme"><meta property="og:image" content="https://acme.test/og.png">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"LocalBusiness"},{"@type":"WebSite"}]}</script>
<script type="application/ld+json">{broken</script></head><body><svg><title>Barnstable: 15 minutes</title></svg><h1>Countertops</h1></body></html>"""

FILES = {
    "/": (200, GOOD),
    "/robots.txt": (200, "User-agent: GPTBot\nUser-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nDisallow: /admin\nSitemap: {base}/sitemap.xml\n"),
    "/sitemap.xml": (200, "<urlset><url><loc>a</loc></url><url><loc>b</loc></url></urlset>"),
    "/llms.txt": (200, "<!doctype html><html>SPA fallback page that is not a real llms.txt file at all</html>"),
    "/llms-full.txt": (200, "# Acme Granite\n\n> Countertops on Cape Cod. Services, service area and contact for language models."),
}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        code, body = FILES.get(self.path, (404, "nope"))
        body = body.replace("{base}", f"http://127.0.0.1:{self.server.server_port}").encode()
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class ChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_page_facts(self):
        f = checks.page_facts(self.base + "/")
        self.assertEqual(f["status"], 200)
        self.assertEqual(f["title"], "Acme Granite | Countertops in Cape Cod")
        self.assertEqual(f["canonical"], "https://acme.test/")
        self.assertEqual(f["lang"], "en")
        self.assertTrue(f["favicon"] and f["apple_touch_icon"])
        self.assertEqual(f["og"]["og:description"], "")
        self.assertEqual(f["json_ld_types"], ["INVALID_JSON_LD", "LocalBusiness", "WebSite"])
        self.assertEqual(f["h1"], ["Countertops"])

    def test_robots_blocks_named_ai_bots_only(self):
        r = checks.robots_facts(self.base)
        self.assertEqual(r["ai_bots_blocked"], ["GPTBot", "ClaudeBot"])
        self.assertFalse(r["wildcard_blocks_all"])
        self.assertEqual(r["sitemaps"], [self.base + "/sitemap.xml"])

    def test_sitemap_counts_urls(self):
        s = checks.sitemap_facts(self.base, [self.base + "/sitemap.xml"])
        self.assertEqual((s["status"], s["url_count"]), (200, 2))

    def test_llms_html_fallback_is_not_ok(self):
        l = checks.llms_facts(self.base)
        self.assertFalse(l["/llms.txt"]["ok"])
        self.assertTrue(l["/llms-full.txt"]["ok"])

    def test_real_404(self):
        self.assertTrue(checks.not_found_facts(self.base)["real_404"])
        FILES["/golive-gate-missing-page-7f3a"] = (200, "soft 404")
        try:
            self.assertFalse(checks.not_found_facts(self.base)["real_404"])
        finally:
            del FILES["/golive-gate-missing-page-7f3a"]


if __name__ == "__main__":
    unittest.main()
