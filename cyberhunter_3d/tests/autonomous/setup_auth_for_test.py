import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from playwright.sync_api import sync_playwright
from run_web import app, db
from cyberhunter_3d.web.models import User
import pyotp

def setup_auth(playwright):
    # Ensure the output directory exists
    output_dir = "jules-scratch/verification"
    os.makedirs(output_dir, exist_ok=True)
    auth_file = os.path.join(output_dir, "auth.json")

    otp_secret = "FWPQ7CKOCOA7P4S7IS3CXONMB756FAED"

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Login with username and password
    page.goto("http://localhost:5001/login")
    page.get_by_label("Username").fill("test")
    page.get_by_label("Password").fill("password")
    page.get_by_role("button", name="Login").click()

    # Now we should be on the 2FA page
    page.wait_for_url("http://localhost:5001/verify-2fa")

    # Generate the current OTP and fill it in
    totp = pyotp.TOTP(otp_secret)
    otp_token = totp.now()
    page.get_by_label("6-Digit Code").fill(otp_token)
    page.get_by_role("button", name="Verify").click()

    # Wait for the dashboard to confirm login
    page.wait_for_url("http://localhost:5001/dashboard")
    print("Successfully logged in and reached dashboard.")

    # Save storage state
    context.storage_state(path=auth_file)
    print(f"Authentication state saved to {auth_file}")

    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        setup_auth(playwright)
