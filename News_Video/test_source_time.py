import unittest
from build_film import source_publication_label

class SourceTimeChecks(unittest.TestCase):
    def test_exact_timestamp_shows_beijing_minute(self):
        self.assertEqual(source_publication_label(dict(published='2026-10-26T05:48:30Z')),'2026.10.26 13:48 北京时间')
    def test_date_only_never_fabricates_minute(self):
        self.assertEqual(source_publication_label(dict(published='2026-10-26T00:00:00+00:00',published_precision='date')),'2026.10.26')
        self.assertEqual(source_publication_label(dict(published='2026-10-26')),'2026.10.26')
    def test_unknown_timezone_is_not_silently_beijing(self):
        self.assertIn('时区未提供',source_publication_label(dict(published='2026-10-26T05:48:00')))
    def test_missing_time_is_explicit(self):
        self.assertEqual(source_publication_label({}),'发布时间未提供')
