import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db
from cyberhunter_3d.web.models import User, Scan
from cyberhunter_3d.core.feeds.feed_manager import check_for_new_targets

def mock_get_hackerone_scopes(api_user, api_key):
    print("MOCK: Returning fake HackerOne scopes.")
    return [
        {
            'name': 'test-program-1',
            'targets': ['test.com'],
            'in_scope_rules': 'test.com is in scope.',
            'out_of_scope_rules': 'anything else is out of scope.'
        }
    ]

with app.app_context():
    # 1. Create a user with a dummy H1 key
    user = User.query.filter_by(username='test').first()
    if not user:
        print("Error: test user not found.")
        exit(1)

    user.hackerone_username = 'test'
    user.hackerone_api_key = 'dummy-key'
    db.session.commit()
    print("Added dummy H1 credentials to test user.")

    # 2. Mock the h1 client
    with unittest.mock.patch('cyberhunter_3d.core.feeds.feed_manager.get_hackerone_scopes', new=mock_get_hackerone_scopes):
        # 3. Run the feed manager
        check_for_new_targets(app)

    # 4. Check for results
    scan = Scan.query.filter_by(hackerone_program_handle='test-program-1').first()
    if scan:
        print("Test PASSED: New scan was created successfully.")
        print(f"  - Scan ID: {scan.id}")
        print(f"  - Targets: {[t.value for t in scan.targets]}")
    else:
        print("Test FAILED: No new scan was created.")
