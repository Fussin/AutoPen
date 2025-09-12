from playwright.sync_api import sync_playwright, expect
import time

def run_verification(playwright):
    browser = playwright.chromium.launch(headless=True)
    # Create a new context with the saved authentication state
    context = browser.new_context(storage_state="jules-scratch/verification/auth.json")
    page = context.new_page()

    # Go directly to the dashboard, we are already logged in
    page.goto("http://localhost:5001/dashboard")
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()

    # Submit a scan
    page.get_by_label("Enter Targets (one per line)").fill("example.com")
    page.get_by_role("button", name="Start Scan").click()

    # Wait for discovery to finish and find the review link
    print("Waiting for discovery phase to complete...")
    time.sleep(20) # Wait for discovery phase
    page.reload()

    review_link = page.get_by_role("link", name="Review & Launch")
    expect(review_link).to_be_visible()

    # Launch the scan from the review page
    review_link.click()
    page.wait_for_url("**/review/*")
    page.get_by_role("button", name="Launch Scan on").click()

    # Go back to dashboard and wait for scan to complete
    page.goto("http://localhost:5001/dashboard")
    print("Waiting for execution phase to complete...")
    time.sleep(10) # Wait for execution phase
    page.reload()

    # Find the completed scan and go to results
    page.get_by_role("link", name="View Results").first.click()
    page.wait_for_url("**/scan/*")

    # Click the graph view link
    page.get_by_role("link", name="View Graph").click()
    page.wait_for_url("**/graph/*")

    # Wait for the graph to be rendered
    print("Waiting for graph to render...")
    expect(page.locator(".mermaid svg")).to_be_visible(timeout=10000)

    # Take a screenshot
    print("Taking screenshot...")
    page.screenshot(path="jules-scratch/verification/graph_view.png")
    print("Screenshot saved to jules-scratch/verification/graph_view.png")

    browser.close()

with sync_playwright() as playwright:
    run_verification(playwright)
