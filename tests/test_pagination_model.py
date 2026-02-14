import unittest

from src.table_parser_model import TableParserModel


class TestPaginationModel(unittest.TestCase):
    def setUp(self):
        self.model = TableParserModel()

    def test_query_param_helpers(self):
        url = "https://example.com/search?q=test&page=1"
        self.assertEqual(self.model._get_query_param_int(url, "page"), 1)
        updated = self.model._set_query_param(url, "page", 2)
        self.assertIn("page=2", updated)
        self.assertEqual(self.model._get_query_param_int(updated, "page"), 2)

    def test_discover_next_page_via_rel_next(self):
        html = """
        <html><head><link rel="next" href="/search?page=3"></head><body></body></html>
        """
        next_url = self.model._discover_next_page_url("https://example.com/search?page=2", html, 2)
        self.assertEqual(next_url, "https://example.com/search?page=3")

    def test_discover_next_page_via_query_fallback(self):
        html = "<html><body><div>No explicit next link</div></body></html>"
        next_url = self.model._discover_next_page_url("https://example.com/search?page=4", html, 4)
        self.assertEqual(next_url, "https://example.com/search?page=5")

    def test_content_fingerprint_changes_with_content(self):
        a = self.model._content_fingerprint("<html>a</html>")
        b = self.model._content_fingerprint("<html>b</html>")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
