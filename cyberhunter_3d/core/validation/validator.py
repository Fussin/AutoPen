import logging
import asyncio
from playwright.async_api import async_playwright, TimeoutError

log = logging.getLogger(__name__)

async def validate_xss(url: str) -> bool:
    """
    Validates a potential Reflected XSS vulnerability by checking for a JavaScript alert.

    Args:
        url: The URL to test, including the payload.

    Returns:
        True if an alert dialog is detected, False otherwise.
    """
    log.info(f"Attempting to validate XSS at: {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Listen for the 'dialog' event, which is triggered by alerts.
            alert_triggered = asyncio.Event()
            page.on("dialog", lambda dialog: alert_triggered.set())

            # Navigate to the URL and wait for the dialog.
            # We give it a short timeout because if the XSS is real, the alert should be fast.
            await page.goto(url, wait_until="domcontentloaded")

            try:
                await asyncio.wait_for(alert_triggered.wait(), timeout=3)
                log.info(f"XSS VALIDATED at {url}")
                await browser.close()
                return True
            except asyncio.TimeoutError:
                log.info(f"XSS NOT validated at {url} (timeout waiting for alert).")
                await browser.close()
                return False

    except TimeoutError:
        log.warning(f"Navigation timeout while validating XSS at: {url}")
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred during XSS validation for {url}: {e}")
        return False
