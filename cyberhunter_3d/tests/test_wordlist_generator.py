import unittest
from cyberhunter_3d.core.reconnaissance.ai.wordlist_generator import extract_keywords_from_subdomains, generate_intelligent_wordlist

class TestWordlistGenerator(unittest.TestCase):

    def test_extract_keywords(self):
        subdomains = [
            "dev.api.example.com",
            "staging-api.example.com",
            "test.vpn.example.com",
            "www.example.com",
            "mail.example.com",
        ]

        keywords = extract_keywords_from_subdomains(subdomains)

        self.assertIn("api", keywords)
        self.assertIn("staging", keywords)
        self.assertIn("vpn", keywords)
        self.assertNotIn("www", keywords)
        self.assertNotIn("mail", keywords)

    def test_generate_wordlist(self):
        keywords = ["api", "staging"]
        wordlist = generate_intelligent_wordlist(keywords)

        self.assertIn("api", wordlist)
        self.assertIn("staging", wordlist)
        self.assertIn("dev-api", wordlist)
        self.assertIn("staging-uat", wordlist)

if __name__ == '__main__':
    unittest.main()
