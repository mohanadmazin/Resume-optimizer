"""Run this ONCE, manually, to get past Indeed's Cloudflare "Just a
moment..." challenge and save the resulting clearance cookie into
./indeed_profile. After this, job_scraper.py can reuse that saved
session headlessly instead of hitting the challenge page every time.

Usage:
    python indeed_login.py

A real Chrome window will open at an Indeed job search page. Wait for
the "Just a moment..." check to finish and the real page to load (this
is usually automatic, a few seconds - if it shows an interactive
checkbox/puzzle, solve it). Once you see the actual Indeed page with
job listings, come back to the terminal and press Enter to save and
close.

Cloudflare clearance cookies are typically scoped to the browser
fingerprint they were issued to and expire after a while (anywhere
from ~30 minutes to a day or more depending on Indeed's settings) -
if fetches start failing again later, just re-run this script.
"""
from playwright.sync_api import sync_playwright

PROFILE_DIR = "./indeed_profile"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,  # must be visible so the CF challenge can pass / you can solve it
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Kuala_Lumpur",
            user_agent=USER_AGENT,
        )

        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page.goto("https://malaysia.indeed.com/", wait_until="domcontentloaded")

        print("\nA browser window has opened at Indeed.")
        print("Wait for the 'Just a moment...' check to clear (usually automatic).")
        print("If an interactive challenge appears, solve it.")
        print("Once you see the real Indeed homepage, come back here and press Enter.\n")
        input("Press Enter once the real page has loaded to save the session and close... ")

        context.close()
        print(f"Session saved to {PROFILE_DIR}. You can now run job_scraper.py headlessly.")


if __name__ == "__main__":
    main()
