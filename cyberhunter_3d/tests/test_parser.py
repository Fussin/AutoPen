import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.target_parser import parse_targets

class TestTargetParser(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(parse_targets([]), [])
        self.assertEqual(parse_targets(['', '   ', '\n']), [])

    def test_domains(self):
        inputs = ['example.com', 'sub.example.co.uk']
        expected = [
            ('example.com', 'domain'),
            ('sub.example.co.uk', 'domain')
        ]
        self.assertEqual(parse_targets(inputs), expected)

    def test_wildcard_domains(self):
        inputs = ['*.example.com', '*.sub.example.net']
        expected = [
            ('example.com', 'wildcard_domain'),
            ('sub.example.net', 'wildcard_domain')
        ]
        self.assertEqual(parse_targets(inputs), expected)

    def test_ip_addresses(self):
        inputs = ['192.168.1.1', '8.8.8.8']
        expected = [
            ('192.168.1.1', 'ip_address'),
            ('8.8.8.8', 'ip_address')
        ]
        self.assertEqual(parse_targets(inputs), expected)

    def test_cidrs(self):
        inputs = ['192.168.1.0/24', '10.0.0.0/8']
        expected = [
            ('192.168.1.0/24', 'cidr'),
            ('10.0.0.0/8', 'cidr')
        ]
        self.assertEqual(parse_targets(inputs), expected)

    def test_asns(self):
        inputs = ['AS15169', 'as1234', '5678']
        expected = [
            ('15169', 'asn'),
            ('1234', 'asn'),
            ('5678', 'asn')
        ]
        self.assertEqual(parse_targets(inputs), expected)

    def test_mixed_valid_inputs(self):
        inputs = [
            'example.com',
            '*.google.com',
            '1.1.1.1',
            '8.8.0.0/16',
            '   whitespace.com   ',
            'AS15169'
        ]
        expected = [
            ('example.com', 'domain'),
            ('google.com', 'wildcard_domain'),
            ('1.1.1.1', 'ip_address'),
            ('8.8.0.0/16', 'cidr'),
            ('whitespace.com', 'domain'),
            ('15169', 'asn')
        ]
        # The order might not be guaranteed, so we'll sort both lists
        self.assertCountEqual(parse_targets(inputs), expected)

    def test_invalid_inputs(self):
        # This test verifies that inputs that are clearly invalid are filtered out.
        inputs = ['invalid-tld', '1.2.3.256', '1.2.3.4/33', '..invalid.com', '-another.com']
        self.assertEqual(parse_targets(inputs), [])

    def test_mixed_valid_and_invalid(self):
        inputs = [
            'example.com',
            'invalid..com', # Invalid
            '8.8.8.8',
            '999.999.999.999', # Invalid
            '*.good.net',
            '10.0.0.0/8'
        ]
        expected = [
            ('example.com', 'domain'),
            ('8.8.8.8', 'ip_address'),
            ('good.net', 'wildcard_domain'),
            ('10.0.0.0/8', 'cidr')
        ]
        self.assertCountEqual(parse_targets(inputs), expected)

if __name__ == '__main__':
    unittest.main()
