import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.smart_priority import classify_asset, CRITICAL, HIGH, MEDIUM, LOW

class TestSmartPriority(unittest.TestCase):

    def test_critical_priority(self):
        self.assertEqual(classify_asset("http://example.com/login"), CRITICAL)
        self.assertEqual(classify_asset("http://example.com/admin/dashboard"), CRITICAL)
        self.assertEqual(classify_asset("https://example.com/api/v1/payments"), CRITICAL)
        self.assertEqual(classify_asset("https://example.com/upload/file"), CRITICAL)

    def test_high_priority(self):
        self.assertEqual(classify_asset("http://example.com/search?q=test"), HIGH)
        self.assertEqual(classify_asset("http://example.com/profile/user1"), HIGH)
        self.assertEqual(classify_asset("https://example.com/api/v2/data"), HIGH)

    def test_medium_priority(self):
        self.assertEqual(classify_asset("http://example.com/static/style.css"), MEDIUM)
        self.assertEqual(classify_asset("http://example.com/blog/post1"), MEDIUM)
        self.assertEqual(classify_asset("http://example.com/info.html?id=123"), MEDIUM)

    def test_low_priority(self):
        self.assertEqual(classify_asset("http://example.com/assets/image.png"), LOW)
        self.assertEqual(classify_asset("http://example.com/robots.txt"), LOW)
        self.assertEqual(classify_asset("http://example.com/sitemap.xml"), LOW)
        self.assertEqual(classify_asset("http://example.com/main.js"), LOW)

    def test_default_priority(self):
        self.assertEqual(classify_asset("http://example.com/"), LOW)
        self.assertEqual(classify_asset("http://example.com/about-us"), LOW)

if __name__ == '__main__':
    unittest.main()
