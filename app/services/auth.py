"""Authentication functions for LinkedIn."""

import asyncio
import logging
import os
import time
from typing import Optional, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError,async_playwright
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from app.core.exceptions import AuthenticationError
from app.core.utils import detect_rate_limit

logger = logging.getLogger(__name__)


async def warm_up_browser(page: Page) -> None:
    """
    Visit normal sites to gather cookies and appear more human-like.

    This helps avoid LinkedIn security checkpoints by establishing
    a normal browsing pattern before visiting LinkedIn.

    Args:
        page: Playwright page object
    """
    sites = [
        'https://www.google.com',
        'https://www.wikipedia.org',
        'https://www.github.com',
    ]

    logger.info("Warming up browser by visiting normal sites...")

    for site in sites:
        try:
            await page.goto(site, wait_until='domcontentloaded', timeout=10000)
            await asyncio.sleep(1)  # Brief pause
            logger.debug(f"Visited {site}")
        except Exception as e:
            logger.debug(f"Could not visit {site}: {e}")
            continue

    logger.info("Browser warm-up complete")


def load_credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
    """
    Load LinkedIn credentials from .env file.

    Supports both LINKEDIN_EMAIL/LINKEDIN_USERNAME and LINKEDIN_PASSWORD.

    Returns:
        Tuple of (email, password) or (None, None) if not found
    """
    load_dotenv()
    print("JE SUIS ICI")
    # Support both LINKEDIN_EMAIL and LINKEDIN_USERNAME
    email = os.getenv('LINKEDIN_EMAIL') or os.getenv('LINKEDIN_USERNAME')
    password = os.getenv('LINKEDIN_PASSWORD')

    return email, password
async def set_cookies(page):
    # Get all cookies
    cookies = await page.context.cookies()

    # Remove only the lang cookie
    filtered = [c for c in cookies if not (c['name'] == 'lang' and 'linkedin.com' in c['domain'])]

    # Clear all then restore without lang
    await page.context.clear_cookies()
    await page.context.add_cookies(filtered)
    await page.context.add_cookies([{
        "name": "lang",
        "value": "v=2&lang=en-us",
        "domain": ".linkedin.com",
        "path": "/"
    }])

async def login_with_credentials(
    page: Page,
    email: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = 30000,
    warm_up: bool = True
) -> None:
    """
    Login to LinkedIn using email and password.

    Args:
        page: Playwright page object
        email: LinkedIn email (if None, tries to load from .env)
        password: LinkedIn password (if None, tries to load from .env)
        timeout: Timeout in milliseconds
        warm_up: Whether to warm up browser by visiting normal sites first

    Raises:
        AuthenticationError: If login fails
    """
    # Load from .env if not provided
    if not email or not password:
        env_email, env_password = load_credentials_from_env()
        email = email or env_email
        password = password or env_password

    if not email or not password:
        raise AuthenticationError(
            "LinkedIn credentials not provided. "
            "Either pass email/password parameters or set LINKEDIN_EMAIL "
            "and LINKEDIN_PASSWORD in your .env file."
        )
    

    # Now add the english lang cookie
    
    # Warm up browser first to appear more human-like
    if warm_up:
        await warm_up_browser(page)
        

    logger.info("Logging in to LinkedIn...")
    
    try:
        # Navigate to login page
        await page.goto('https://www.linkedin.com/login', wait_until="domcontentloaded")
        print("LINED IN")
        # Check for rate limiting
        await detect_rate_limit(page)
        html_content = await page.content()
        await page.screenshot(path="debug_page.png")
        # Print the URL to see if you were redirected
        print(f"Current URL: {page.url}")
        full_html = await page.evaluate("document.documentElement.outerHTML")
        # Print it to your terminal to find the actual input IDs
        #print(full_html)
        #input()
        # Save it to a local file
        with open("page.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        # Wait for login form
        try:
           await page.wait_for_selector('input[type="email"]:visible', timeout=15000)
        
            
        except PlaywrightTimeoutError:
            input()
            raise AuthenticationError(
                "Login form not found. LinkedIn may have changed their page structure "
                "or the site is experiencing issues."
            )

        # Fill in credentials
        #await page.fill('input[id="«r3»"]', email)
        
        await page.fill('input[type="email"]:visible', email)
        await page.fill('input[type="password"]:visible', password)

        logger.debug("Credentials entered")

        # Click sign in button
        count = await page.locator('button[type="button"]:has-text("Sign in")').count()
        print(f"Found {count} buttons with 'Sign in'")
        await page.locator('button[type="button"]:has-text("Sign in")').last.click()


        # Wait for navigation
        try:
            await page.wait_for_url(
                lambda url: 'feed' in url or 'checkpoint' in url or 'authwall' in url,
                timeout=timeout
            )
        except PlaywrightTimeoutError:
            # Check if we're still on login page
            if 'login' in page.url:
                raise AuthenticationError(
                    "Login failed. Please check your credentials. "
                    "The page did not navigate after clicking sign in."
                )

        # Check for various post-login states
        current_url = page.url

        # Check for security checkpoint
        if 'checkpoint' in current_url or 'challenge' in current_url:
            input()
            raise AuthenticationError(
                "LinkedIn security checkpoint detected. "
                "You may need to verify your identity manually. "
                "Consider using session persistence after manual verification. "
                f"Current URL: {current_url}"
            )

        # Check for auth wall
        if 'authwall' in current_url:
            raise AuthenticationError(
                "Authentication wall encountered. "
                "LinkedIn may be blocking automated access. "
                f"Current URL: {current_url}"
            )

        # Verify we're logged in by polling is_logged_in()
        start_time = time.time()
        logged_in = False
        while (time.time() - start_time) * 1000 < 5000:
            if await is_logged_in(page):
                logger.info("✓ Successfully logged in to LinkedIn")
                logged_in = True
                break
            await asyncio.sleep(0.5)  # Poll every 500ms

        if not logged_in:
            # Timeout: couldn't verify within 5s but may still be logged in
            logger.warning(
                "Could not verify login by finding navigation element. "
                "Proceeding anyway..."
            )

    except PlaywrightTimeoutError as e:
        raise AuthenticationError(
            f"Login timed out: {e}. "
            "This could indicate network issues or LinkedIn blocking the request."
        )
    except Exception as e:
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(f"Unexpected error during login: {e}")


async def login_with_cookie(page: Page, cookie_value: str) -> None:
     """
     Login to LinkedIn using li_at cookie.

     Args:
         page: Playwright page object
         cookie_value: Value of li_at cookie

     Raises:
         AuthenticationError: If cookie login fails
     """
     logger.info("Logging in with cookie...")

     try:
         # Set the cookie
         await page.context.add_cookies([{
             "name": "li_at",
             "value": cookie_value,
             "domain": ".linkedin.com",
             "path": "/"
         }])

         # Navigate to feed to verify
         await page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')

         # Check if we're redirected to login (cookie invalid)
         if 'login' in page.url or 'authwall' in page.url:
             raise AuthenticationError(
                 "Cookie authentication failed. The cookie may be expired or invalid."
             )

         # Verify login by polling is_logged_in()
         start_time = time.time()
         logged_in = False
         while (time.time() - start_time) * 1000 < 5000:
             if await is_logged_in(page):
                 logger.info("✓ Successfully authenticated with cookie")
                 logged_in = True
                 break
             await asyncio.sleep(0.5)  # Poll every 500ms

         if not logged_in:
             # Timeout: couldn't verify within 5s but may still be logged in
             logger.warning(
                 "Could not verify cookie login. "
                 "Proceeding anyway..."
             )

     except Exception as e:
         if isinstance(e, AuthenticationError):
             raise
         raise AuthenticationError(f"Cookie authentication error: {e}")


async def is_logged_in(page: Page) -> bool:
    """
    Check if currently logged in to LinkedIn.

    Args:
        page: Playwright page object

    Returns:
        True if logged in, False otherwise
    """
    try:
        current_url = page.url
        print(current_url)
        if current_url=="https://www.linkedin.com/feed/":
            print("Logged in")
            return true
        # Step 1: Fail-fast on auth blockers
        """ auth_blockers = ['/login', '/authwall', '/checkpoint', '/challenge', '/uas/login', '/uas/consumer-email-challenge']
        if any(pattern in current_url for pattern in auth_blockers):
            return False

        # Step 2: Selector check (PRIMARY) - check for nav elements
        old_selectors = '.global-nav__primary-link, [data-control-name="nav.settings"]'
        old_count = await page.locator(old_selectors).count()

        new_selectors = 'nav a[href*="/feed"], nav button:has-text("Home"), nav a[href*="/mynetwork"]'
        new_count = await page.locator(new_selectors).count()

        has_nav_elements = old_count > 0 or new_count > 0

        # Step 3: URL fallback - check for authenticated-only pages
        authenticated_only_pages = ['/feed', '/mynetwork', '/messaging', '/notifications']
        is_authenticated_page = any(pattern in current_url for pattern in authenticated_only_pages)

        # Return True if either nav elements found or on authenticated page
        return has_nav_elements or is_authenticated_page"""
    except Exception:
        return False

def is_logged(page):
     page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded", #always use cuzz networkidle will never fire
            timeout=60000

     )

     if "/feed/" in page.url:
        print("Logged in")
        return True
     else:
        print("Not logged in")
        return False


async def wait_for_manual_login(page: Page, timeout: int = 300000) -> None:
    """
    Wait for user to manually complete login (useful for 2FA, CAPTCHA, etc.).

    Args:
        page: Playwright page object
        timeout: Timeout in milliseconds (default: 5 minutes)

    Raises:
        AuthenticationError: If timeout or login not completed
    """
    logger.info(
        "⏳ Please complete the login process manually in the browser. "
        "Waiting up to 5 minutes..."
    )

    start_time = asyncio.get_event_loop().time()

    while True:
        # Check if logged in
        if await is_logged_in(page):
            logger.info("✓ Manual login completed successfully")
            return

        # Check timeout
        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
        if elapsed > timeout:
            raise AuthenticationError(
                "Manual login timeout. Please try again and complete login faster."
            )

        # Wait a bit before checking again
        await asyncio.sleep(1)
async def main():
     async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./linkedin_session",
            headless=False,
            args=["--start-maximized", "--lang=en-US" ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9"
            }

        )
        page = context.pages[0]
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)
        # Apply stealth configuration
        await set_cookies(page)
        await page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')
        input()
        if await is_logged_in(page):
            logger.info("✓ Already logged in via saved session")
        else:
            logger.info("Session expired, logging in again...")
            await login_with_credentials(page)

        input("Complete any remaining login/CAPTCHA steps manually. Press Enter to exit...")

if __name__=="__main__":
    asyncio.run(main())
