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
            # Navigate directly to the login page as requested
            self.page.goto("https://klips2.uni-koeln.de/co/ee/ui/ca2/app/desktop/#/login", timeout=30000)
            
            # Wait for login form elements
            # Use specific IDs provided by user
            try:
                # Username
                self.page.wait_for_selector("#id_brm-pm-dtop_login_uname_input", state="visible", timeout=10000)
                self.page.fill("#id_brm-pm-dtop_login_uname_input", username)
                
                # Password - assuming standard password input or similar ID pattern
                # We'll try a robust selector for password since we don't have the exact ID yet
                self.page.fill("input[type='password']", password)
                
                # Wait for button to become enabled (it starts as disabled)
                submit_selector = "#id_brm-pm-dtop_login_submitbutton"
                
                # Force enable if needed (sometimes Angular validation is slow) or just wait
                # self.page.wait_for_function(f"document.querySelector('{submit_selector}').disabled === false")
                
                # Click login button
                self.page.click(submit_selector, timeout=5000)
                
            except Exception as e:
                print(f"Specific selector login failed: {e}")
                # Fallback to previous generic logic if specific IDs fail (e.g. if page changes)
                print("Trying generic fallback...")
                self.page.fill("input[name='username']", username)
                self.page.fill("input[type='password']", password)
                self.page.click("button[type='submit']", timeout=5000)
            
            # Wait for navigation back to the app
            self.page.wait_for_load_state("networkidle")
            
            # Handle Interstitial "Hooks" page (e.g. News, Terms)
            # Loop a few times in case there are multiple pages or it reloads
            for _ in range(3):
                if "wbEeHooks.showHooks" in self.page.url:
                    print("Interstitial page detected, clicking 'Weiter'...")
                    try:
                        # Try to find a "Weiter" link or button
                        # Use get_by_role to avoid matching large text blocks containing "Weiter"
                        weiter_btn = self.page.get_by_role("link", name="Weiter", exact=True)
                        if weiter_btn.count() > 0:
                            weiter_btn.first.click()
                        else:
                            # Fallback to button
                            self.page.get_by_role("button", name="Weiter").first.click()
                            
                        self.page.wait_for_load_state("networkidle")
                        time.sleep(1) # Short pause to allow redirect
                    except Exception as e:
                        print(f"Failed to click 'Weiter': {e}")
                        # Last resort: generic text click but try to be specific to 'a' tag
                        try:
                            self.page.click("a:text-is('Weiter')", timeout=2000)
                        except:
                            pass
                        break
                else:
                    break

            # Verify login success
            # Check for elements that only exist when logged in
            # e.g. "Logout", "Abmelden", or user profile icon
            # Or check if we are NOT on the login page anymore
            
            if self.page.locator("#username").is_visible():
                # Still on login page -> failed
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
