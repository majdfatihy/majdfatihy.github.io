import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from scripts import sitemap_sync as sync


class SitemapSyncTests(unittest.TestCase):
    def test_url_normalization_rejects_foreign_and_unsafe_paths(self):
        self.assertEqual(sync.norm("https://dev.majdfatihy.com/tool/index.html"),
                         "https://dev.majdfatihy.com/tool/")
        self.assertIsNone(sync.norm("https://example.org/tool/"))
        self.assertIsNone(sync.norm("https://dev.majdfatihy.com/../private/"))
        self.assertEqual(sync.source_path("https://dev.majdfatihy.com/guide/en/"),
                         ("guide", "en/index.html"))

    def test_creation_and_last_modified_do_not_change_without_content_change(self):
        url = "https://dev.majdfatihy.com/tool/"
        data = {"schema_version": 1, "pages": {}}
        with patch.object(sync, "git_file_dates", return_value=("2026-09-01", "2026-11-02")):
            sync.record_page(data, url, "first-content", "2026-11-23")
        initial = dict(data["pages"][url])
        sync.record_page(data, url, "first-content", "2026-12-01")
        self.assertEqual(data["pages"][url], initial)
        with patch.object(sync, "git_file_dates", return_value=("2026-09-01", "2026-12-03")):
            sync.record_page(data, url, "updated-content", "2026-12-04")
        self.assertEqual(data["pages"][url]["created_at"], "2026-09-01")
        self.assertEqual(data["pages"][url]["first_seen"], "2026-11-23")
        self.assertEqual(data["pages"][url]["lastmod"], "2026-12-03")
        with patch.object(sync, "git_file_dates", return_value=(None, None)):
            sync.record_page(data, url, "unverifiable-change", "2026-12-06")
        self.assertNotIn("lastmod", data["pages"][url])
        self.assertEqual(data["pages"][url]["created_at"], "2026-09-01")

    def test_existing_urls_are_preserved_and_render_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data/site.json").write_text(
                '{"pages":[{"slug":"index"}]}', encoding="utf-8")
            (root / "data/projects.json").write_text(
                '{"projects":[{"url":"https://dev.majdfatihy.com/tool/"}]}',
                encoding="utf-8")
            site = root / "sitemap.xml"
            site.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://dev.majdfatihy.com/</loc>'
                '<lastmod>2026-10-22</lastmod></url>'
                '<url><loc>https://dev.majdfatihy.com/old/</loc></url>'
                '</urlset>\n', encoding="utf-8")
            with patch.object(sync, "ROOT", root), patch.object(sync, "SITEMAP", site):
                data = {"schema_version": 1, "pages": {}}
                sync.render(data)
                xml = ET.parse(site)
                locs = [el.text for el in xml.getroot().iter()
                        if el.tag.endswith("}loc")]
                self.assertEqual(len(locs), 3)
                self.assertIn("https://dev.majdfatihy.com/old/", locs)
                self.assertIn("2026-10-22", site.read_text("utf-8"))
                before = site.read_bytes()
                sync.render(data)
                self.assertEqual(before, site.read_bytes())

    def test_noindex_urls_are_excluded_from_registry_sitemap_and_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data/site.json").write_text(
                '{"pages":[{"slug":"index"}]}', encoding="utf-8")
            (root / "data/projects.json").write_text(
                '{"projects":[{"url":"https://dev.majdfatihy.com/tool/"},'
                '{"url":"https://dev.majdfatihy.com/redirect/"}]}',
                encoding="utf-8")
            site = root / "sitemap.xml"
            site.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://dev.majdfatihy.com/</loc></url>'
                '<url><loc>https://dev.majdfatihy.com/redirect/</loc></url>'
                '</urlset>\n', encoding="utf-8")
            data = {"schema_version": 1, "pages": {
                "https://dev.majdfatihy.com/redirect/": {"noindex": True}
            }}
            with patch.object(sync, "ROOT", root), patch.object(sync, "SITEMAP", site):
                sync.render(data)
                xml = ET.parse(site)
                locs = [el.text for el in xml.getroot().iter()
                        if el.tag.endswith("}loc")]
                self.assertIn("https://dev.majdfatihy.com/", locs)
                self.assertIn("https://dev.majdfatihy.com/tool/", locs)
                self.assertNotIn("https://dev.majdfatihy.com/redirect/", locs)

    def test_robots_meta_blocks_new_page(self):
        url = "https://dev.majdfatihy.com/tool/"
        base = (f'<html><head><title>Useful tool</title>'
                f'<link rel="canonical" href="{url}">'
                f'</head><body><main>{"Useful public project description. " * 12}'
                f'</main></body></html>')
        with patch.object(sync, "get", return_value=(
                base.encode(), url, {"Content-Type": "text/html"})):
            page, error = sync.inspect(url)
            self.assertIsNone(error)
            self.assertTrue(page["hash"])
        blocked = base.replace('</head>', '<meta name="robots" content="noindex"></head>')
        with patch.object(sync, "get", return_value=(
                blocked.encode(), url, {"Content-Type": "text/html"})):
            page, error = sync.inspect(url)
            self.assertIsNone(page)
            self.assertIn("noindex", error)


if __name__ == "__main__":
    unittest.main()
