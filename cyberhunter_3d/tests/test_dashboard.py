import pytest
from unittest.mock import patch

def test_historical_intelligence_page(client):
    """
    Tests that the historical intelligence page loads for an authenticated user.
    """
    with patch('pyotp.TOTP.verify', return_value=True):
        # 1. Login first
        client.post('/login', data={'username': 'testuser', 'password': 'password'}, follow_redirects=True)
        # 2. Then verify 2FA
        response = client.post('/verify-2fa', data={'token': '123456'}, follow_redirects=True)
        assert response.status_code == 200 # Should be on dashboard

        # 3. Now access the protected page
        response = client.get('/historical-intelligence')
        assert response.status_code == 200
        assert b"Historical Intelligence" in response.data
        assert b"Subdomain Growth" in response.data
        assert b"Live Host Growth" in response.data
        assert b"New Technologies Discovered" in response.data
