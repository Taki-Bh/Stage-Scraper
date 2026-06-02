# app/scraping/base_scraper.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page
import random
import time
from app.core.config import *
import json
import requests
import re
import time
from urllib.parse import quote



def fetch_job_details(job_id, headers):
    """
    Step 2 (Resilient GraphQL Parser): Queries the unified GraphQL layer
    and uses flexible regex patterns to extract content.
    """
    base_url = "https://www.linkedin.com/voyager/api/graphql"
    query_id = "voyagerJobsDashJobPostingDetailSections.2bf6cded247cb2f6cc7dcda5558af592"
    variables = f"(cardSectionTypes:List(TOP_CARD,HOW_YOU_FIT_CARD),jobPostingUrn:urn%3Ali%3Afsd_jobPosting%3A{job_id},includeSecondaryActionsV2:true,jobDetailsContext:(isJobSearch:true))"

    target_url = f"{base_url}?variables={variables}&queryId={query_id}"

    details_headers = headers.copy()
    details_headers["Accept"] = "application/json"

    job_data = {
        "job_id": job_id,
        "title": "N/A",
        "description": "N/A"
    }

    try:
        response = requests.get(target_url, headers=details_headers)

        if response.status_code == 200:
            response_text = response.text

            # 🛠️ LOOSER TITLE REGEX: Finds "title":"..." without worrying about what key follows it
            # We look specifically for the title field closest to the job posting metadata
            title_matches = re.findall(r'"title":"([^"]+)"', response_text)
            if title_matches:
                # The first few titles in this specific GraphQL endpoint are almost always the job title
                # and company name. We grab index 0.
                job_data["title"] = title_matches[0]

            # 🛠️ LOOSER DESCRIPTION REGEX: In GraphQL, text segments are often labeled as "text"
            # inside text objects or paragraphs. We look for the longest text block.
            all_text_blocks = re.findall(r'"text":"([^"]+)"', response_text)
            if all_text_blocks:
                # The job description is by far the largest text block in the payload.
                # We sort by character length and pick the biggest one.
                longest_block = max(all_text_blocks, key=len)

                # Clean up typical JSON escape artifacts
                clean_desc = longest_block.replace("\\n", "\n").replace('\\"', '"')
                job_data["description"] = clean_desc

            # Diagnostic Fallback: If it STILL says N/A, let's peek at the structure
            if job_data["title"] == "N/A":
                print(f"    [!] Debug: Sample response text slice: {response_text[:400]}")

        else:
            print(f"    [!] Couldn't parse ID {job_id}. Status Code: {response.status_code}")

    except Exception as e:
        print(f"    [!] Error connection execution on ID {job_id}: {e}")

    return job_data
if __name__ == "__main__":
    search_term = "machine learning intern"
    print(f"[*] Initializing Step 1: Querying index list for '{search_term}'...")

    target_ids, active_headers = fetch_linkedin_job_ids(keyword=search_term, total_jobs_to_fetch=25)
    total_found = len(target_ids)
    print(f"[+] Successfully indexed {total_found} Job IDs. Starting Step 2 detail extraction loop...\n")

    scraped_dataset = []

    # Process the first 3 jobs as a quick sanity check before processing all 25
    for index, j_id in enumerate(target_ids[:3], start=1):
        print(f"[*] [{index}/3] Processing Job ID: {j_id}...")
        single_job_parsed = fetch_job_details(j_id, active_headers)

        print(f"    [✔] Title Extracted: {single_job_parsed['title']}")
        scraped_dataset.append(single_job_parsed)
        time.sleep(2.5)

    print("\n" + "="*60)
    print(f"[FINISHED] Diagnostic run complete. Extracted data for {len(scraped_dataset)} jobs.")
    print("="*60)
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
        self.jobs = []
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
        try:
            self.page.screenshot(
                path="debug_view.png",
                timeout=3000,
                animations="disabled",
                wait_until="domcontentloaded"
            )
        except Exception as e:
            print("Screenshot skipped:", e)
            print("Page exists!")
        return self.page.content()


    def handle_response(self, response):
        try:
            url = response.url

            if "voyagerJobsDashJobCards" not in url:
                return

            data = response.json()
            
            with open("output.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("RAW KEYS:", data.keys())
            print("RAW SAMPLE:", data)

            elements = (
                data.get("data", {})
                    .get("jobSearch", {})
                    .get("elements", [])
            )

            if not hasattr(self, "jobs"):
                self.jobs = []

            self.jobs.extend(elements)

            print(f"Captured {len(elements)} jobs | Total: {len(self.jobs)}")

        except Exception as e:
            print("Error:", e)





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
        scrollable = self.page.locator(".scaffold-layout__list > div").first
        print(scrollable.evaluate("""
        el => ({
            overflow: getComputedStyle(el).overflowY,
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight
        })
        """))


        self.page.on("response", self.handle_response)
        for _ in range(10):
            scrollable.evaluate("""
            el => el.scrollBy(0, 500)
            """)
            self.page.wait_for_timeout(100)



    

        
    def _random_delay(self) -> None:
        """
        Random human-like delay.
        """

        delay = random.uniform(
            self.delay_range[0],
            self.delay_range[1]
        )

        time.sleep(delay)