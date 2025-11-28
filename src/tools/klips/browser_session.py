import time
import os
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright

class KLIPSBrowserSession:
    """
    Manages a Playwright browser session for KLIPS2 interactions.
    Handles initialization, login, and cleanup.
    """
    def __init__(self, headless: Optional[bool] = None):
        if headless is None:
            # Default to True unless KLIPS_HEADLESS env var is set to 'false'
            self.headless = os.getenv("KLIPS_HEADLESS", "true").lower() != "false"
        else:
            self.headless = headless
            
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """Starts the Playwright session."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = self.context.new_page()

    def close(self):
        """Closes the browser and stops Playwright."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def login(self, username, password) -> bool:
        """
        Logs into KLIPS2 using the provided credentials.
        """
        if not self.page:
            raise RuntimeError("Session not started. Call start() or use 'with' statement.")

        try:
            import time as t
            
            # Navigate directly to the login page
            t0 = t.time()
            self.page.goto("https://klips2.uni-koeln.de/co/ee/ui/ca2/app/desktop/#/login", timeout=30000)
            print(f"⏱️  Page load: {t.time() - t0:.2f}s")
            
            # Wait for login form elements
            t0 = t.time()
            try:
                # Username
                self.page.wait_for_selector("#id_brm-pm-dtop_login_uname_input", state="visible", timeout=10000)
                self.page.fill("#id_brm-pm-dtop_login_uname_input", username)
                
                # Password
                self.page.fill("input[type='password']", password)
                
                # Click login button
                submit_selector = "#id_brm-pm-dtop_login_submitbutton"
                self.page.click(submit_selector, timeout=5000)
                
            except Exception as e:
                print(f"Specific selector login failed: {e}")
                print("Trying generic fallback...")
                self.page.fill("input[name='username']", username)
                self.page.fill("input[type='password']", password)
                self.page.click("button[type='submit']", timeout=5000)
            print(f"⏱️  Login form fill & submit: {t.time() - t0:.2f}s")
            
            # Wait for navigation after login
            t0 = t.time()
            self.page.wait_for_load_state("domcontentloaded")
            print(f"⏱️  Post-login wait: {t.time() - t0:.2f}s")
            
            # Handle Interstitial "Hooks" page (e.g. News, Terms)
            # Check both URL pattern AND presence of "Weiter" button
            t0 = t.time()
            interstitial_count = 0
            for _ in range(5):
                time.sleep(0.2)  # Brief pause for page to settle
                current_url = self.page.url
                
                # Check for interstitial by URL or by presence of "Weiter" link
                is_interstitial = "wbEeHooks.showHooks" in current_url
                weiter_btn = self.page.locator("a:text-is('Weiter')").first
                has_weiter = weiter_btn.count() > 0 and weiter_btn.is_visible()
                
                if is_interstitial or has_weiter:
                    interstitial_count += 1
                    print(f"Interstitial page #{interstitial_count} detected, clicking 'Weiter'...")
                    try:
                        weiter_btn.click(timeout=2000)
                        self.page.wait_for_load_state("domcontentloaded")
                    except Exception as e:
                        print(f"Failed to click 'Weiter': {e}")
                        break
                elif "login" in current_url.lower():
                    time.sleep(0.2)
                else:
                    break
            print(f"⏱️  Interstitial handling ({interstitial_count} pages): {t.time() - t0:.2f}s")

            # Verify login success
            if self.page.locator("#id_brm-pm-dtop_login_uname_input").is_visible():
                print("Login input still visible. Login likely failed.")
                return False
                
            return True

        except Exception as e:
            print(f"Login failed with error: {e}")
            # Capture screenshot for debugging if needed
            # self.page.screenshot(path="login_failed.png")
            return False

    def navigate_to_application(self):
        """Navigates to the application wizard/page."""
        # This will be specific to the 'Apply' tool
        # Usually "Studienbewerbung" or similar in the menu
        pass
