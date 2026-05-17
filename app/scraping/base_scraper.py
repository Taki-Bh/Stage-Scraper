# app/scraping/base_scraper.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page
import random
import time
from app.core.config import *

class BaseScraper(ABC):
    """
    Abstract Playwright-based scraper.

    All site scrapers should inherit from this class.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        delay_range: tuple = (1, 3),
    ) -> None:

        self.headless = headless
        self.timeout = timeout
        self.delay_range = delay_range

        # Playwright objects
        self.playwright = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    def start(self) -> None:
        """
        Start Playwright browser session.
        """

        self.playwright = sync_playwright().start()

        context = self.playwright.chromium.launch_persistent_context(
        user_data_dir=CONFIG["USER-DATA"],
        executable_path=CONFIG["PATH"],
        headless=False,
        args=[
            f"--profile-directory={PROFILE}"
        ]
        )

        if context.pages:
            self.page = context.pages[0]
        else:
            self.page = context.new_page()

        self.page.set_default_timeout(self.timeout)


    def close(self) -> None:
        """
        Cleanup browser resources.
        """

        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()

    # -------------------------------------------------
    # Abstract API
    # -------------------------------------------------

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraper method.

        Must be implemented by subclasses.
        """
        pass

    # -------------------------------------------------
    # Shared utilities
    # -------------------------------------------------

    def visit(self, url: str) -> None:
        """
        Navigate to a page.
        """

        if not self.page:
            raise RuntimeError(
                "Browser not initialized. Call start()."
            )

        self._random_delay()

        self.page.goto(
            url,
            wait_until="domcontentloaded"
        )

    def get_html(self) -> str:
        """
        Return current page HTML.
        """

        if not self.page:
            raise RuntimeError(
                "Page not initialized."
            )
        self.page.screenshot(path="debug_view.png")
        print("Page exists!")
        return self.page.content()

    def scroll_page(
        self,
        scroll_count: int = 5,
        scroll_pause: float = 1.5,
    ) -> None:
        """
        Simulate human-like scrolling.
        """

        if not self.page:
            raise RuntimeError(
                "Page not initialized."
            )

        for _ in range(scroll_count):

            self.page.mouse.wheel(0, 3000)

            time.sleep(scroll_pause)

    def _random_delay(self) -> None:
        """
        Random human-like delay.
        """

        delay = random.uniform(
            self.delay_range[0],
            self.delay_range[1]
        )

        time.sleep(delay)