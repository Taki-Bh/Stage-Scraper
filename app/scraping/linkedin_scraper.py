# app/scraping/linkedin.py

from typing import List, Dict, Any
from bs4 import BeautifulSoup

from app.scraping.base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):

    BASE_URL = (
        "https://www.linkedin.com/jobs/search/"
        "?keywords=Python%20Developer"
        "&location=Remote"
    )

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape LinkedIn job cards.
        """

        self.start()

        jobs: List[Dict[str, Any]] = []

        try:

            print("[LINKEDIN] Opening jobs page...")

            self.visit(self.BASE_URL)

            print("[LINKEDIN] Scrolling page...")

            self.scroll_page(
                scroll_count=8,
                scroll_pause=2
            )

            html = self.get_html()

            soup = BeautifulSoup(html, "html.parser")

            cards = soup.select("div.base-card")

            print(f"[LINKEDIN] Found {len(cards)} job cards")

            for card in cards:

                try:

                    title_element = card.select_one(
                        "h3.base-search-card__title"
                    )

                    company_element = card.select_one(
                        "h4.base-search-card__subtitle"
                    )

                    location_element = card.select_one(
                        "span.job-search-card__location"
                    )

                    link_element = card.select_one(
                        "a.base-card__full-link"
                    )

                    title = (
                        title_element.get_text(strip=True)
                        if title_element else None
                    )

                    company = (
                        company_element.get_text(strip=True)
                        if company_element else None
                    )

                    location = (
                        location_element.get_text(strip=True)
                        if location_element else None
                    )

                    url = (
                        link_element["href"]
                        if link_element else None
                    )

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url,
                    })

                except Exception as e:
                    print(f"[CARD ERROR] {e}")

            return jobs

        finally:

            self.close()