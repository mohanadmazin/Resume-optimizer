"""Run this ONCE, manually, to log into LinkedIn and save the session
into ./linkedin_profile. After this, job_scraper.py can reuse that
saved session headlessly without hitting the authwall.

Usage:
    python linkedin_login.py

A real Chrome window will open. Log in (enter email/password, solve
any 2FA/captcha) as you normally would. Once you can see your LinkedIn
feed, come back to the terminal and press Enter to close and save.
"""
from playwright.sync_api import sync_playwright

PROFILE_DIR = "./linkedin_profile"

HEADERS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,  # must be visible so you can log in
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Asia/Kuala_Lumpur",
            user_agent=HEADERS_UA,
        )

        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        print("\nA browser window has opened.")
        print("Log into LinkedIn manually (handle 2FA/captcha if prompted).")
        print("Once you can see your feed/home page, come back here and press Enter.\n")
        input("Press Enter once logged in to save the session and close... ")

        context.close()
        print(f"Session saved to {PROFILE_DIR}. You can now run job_scraper.py headlessly.")


if __name__ == "__main__":
    main()
