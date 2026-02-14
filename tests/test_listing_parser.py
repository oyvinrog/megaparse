import unittest
from bs4 import BeautifulSoup

from src.parser import (
    extract_listing_records,
    get_tables,
    records_to_table_candidates,
    score_listing_table,
)


class TestListingParser(unittest.TestCase):
    def test_extract_listing_records_from_repeated_cards(self):
        html = """
        <html><body>
          <section>
            <article><a href="/ad/1">Sunny Loft</a><span>4 200 000 kr</span><span>0598 Oslo</span></article>
            <article><a href="/ad/2">City Apartment</a><span>3 900 000 kr</span><span>0579 Oslo</span></article>
            <article><a href="/ad/3">Family Home</a><span>5 100 000 kr</span><span>0560 Oslo</span></article>
          </section>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        records = extract_listing_records(soup, source_url="https://example.com")

        self.assertEqual(len(records), 3)
        self.assertTrue(all(record["listing_url"].startswith("https://example.com/ad/") for record in records))
        self.assertTrue(all(record["price_text"] for record in records))

    def test_extract_listing_records_rejects_navigation(self):
        html = """
        <html><body>
          <ul>
            <li><a href="/about">About us</a></li>
            <li><a href="/pricing">Pricing</a></li>
            <li><a href="/contact">Contact</a></li>
            <li><a href="/help">Help</a></li>
          </ul>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        records = extract_listing_records(soup, source_url="https://example.com")
        self.assertEqual(records, [])

    def test_records_to_table_candidates_and_score(self):
        records = [
            {
                "listing_id": "abc123",
                "source_url": "https://example.com/search",
                "listing_url": "https://example.com/ad/1",
                "title": "Sunny Loft",
                "price_text": "4 200 000 kr",
                "location_text": "0598 Oslo",
                "area_text": "78 m2",
                "rooms_text": "3 rooms",
                "raw_text": "Sunny Loft 4 200 000 kr 0598 Oslo 78 m2 3 rooms",
                "confidence": 0.9,
                "container_signature": "article:2",
            }
        ]
        tables = records_to_table_candidates(records)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].attrs.get("table_type"), "listing_cards")
        self.assertGreater(score_listing_table(tables[0]), 0.5)

    def test_get_tables_includes_html_tables_for_generic_pages(self):
        html = """
        <html><body>
          <table>
            <tr><th>Country</th><th>Rate</th></tr>
            <tr><td>A</td><td>1.2</td></tr>
            <tr><td>B</td><td>2.3</td></tr>
          </table>
        </body></html>
        """
        tables = get_tables(html, source_url="https://example.com")
        self.assertTrue(any(df.shape[0] >= 2 and df.shape[1] >= 2 for df in tables))


if __name__ == "__main__":
    unittest.main()
