from app.scraping.linkedin_scraper import LinkedInScraper
import logging
import app.services.auth  as auth
import asyncio
import os
from app.core.utils import retry_async
from app.core.utils import get_auth_cookies
from playwright.async_api import async_playwright
from app.core.exceptions import AuthenticationError

logger = logging.getLogger("Pipeline")

STATE_FILE="state.json"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
LOCALE="en-US"



async def login(page,email="",password=""):
    if await auth.is_logged(page):
        return
    try:
        if email=="" or password=="":
            await auth.login_with_credentials(page=page,email=password,password=password)

    except AuthenticationError as e:
        
        if "You may need to verify your identity manually" in str(e):
            logger.warning("🚨 LinkedIn identity check caught in exception!")
            await auth.wait_for_manual_login(page)
            # Pause the pipeline so you can handle it
            input("Please resolve the verification in the browser window, then press Enter here...")
        else:
            # It's a completely different error, handle it normally
            logger.error(f"Pipeline failed due to a different error: {e}")

async def login_and_save(context, page):
    """Helper function to handle manual login and save state."""
    await page.goto("https://www.linkedin.com/login")
    input("Log in manually in the browser window, then press Enter here to save session...")
    await context.storage_state(path=STATE_FILE)
    print(f"✅ Saved new session to {STATE_FILE}")

async def get_authenticated_context(browser):
    """Dynamically creates a context based on whether the state file exists."""
    # Check if the file is physically present in your project root
    if os.path.exists(STATE_FILE):
        print("🔐 Found session state! Loading cookies automatically...")
        context = await browser.new_context(
            storage_state=STATE_FILE,
            user_agent=USER_AGENT,
            locale=LOCALE
            )
        page = await context.new_page()
    else:
        print("⚠️ state.json not found! Launching fresh browser for manual login...")
        context = await browser.new_context()
        page = await context.new_page()
        # Run the login flow to generate the missing file
        
    return context, page



class PipelineOrchestrator:
    def run_pipeline(self,keywords) -> None:
        asyncio.run(self._run_pipeline(keywords))

    async def _run_pipeline(self, keywords) -> None:
        logger.info(f"🚀 Kicking off pipeline for: {keywords}")

        """
        Main orchestration pipeline.

        Flow:
            Auth ->Scrape -> Parse -> Normalize -> Score -> Store
        """
            
        # -------------------------------------------------
        # Initialize components
        # -------------------------------------------------

        scraper = LinkedInScraper()

        #parser = JobParser()

        #normalizer = JobNormalizer()

        #scorer = RelevanceScorer()

        #session = get_db_session()

        # -------------------------------------------------
        #-- Authentification
        # -------------------------------------------------
        logger.info("Starting Authentification Process")
        logger.info("Opening the navigator")
        async with async_playwright() as p:
            browser= await p.chromium.launch(
                headless=False,
                args=["--start-maximized", "--lang=en-US" ],
                
            )
            context,page= await get_authenticated_context(browser)
                
            logger.info("Saving acquired cookies for loggin...")
            await login(page,"a","a")
            
            await context.storage_state(path="state.json")
            await browser.close()
            input()





        # -------------------------------------------------
        # Step 1 — Scrape raw jobs
        # -------------------------------------------------
        cookies=get_auth_cookies()
        scraper.set_scraping_cookies(cookies)
        print("[SCRAPING] Scraping cookies were set!")
        print("[SCRAPING] Fetching jobs...")

        raw_jobs = scraper.scrape()

        print(f"[SCRAPING] Retrieved {len(raw_jobs)} raw jobs")

        # -------------------------------------------------
        # Step 2 — Parse jobs
        # -------------------------------------------------
        print(raw_jobs)
        pass
        parsed_jobs = []

        print("[PARSING] Parsing jobs...")

        for raw_job in raw_jobs:

            try:
                parsed_job = parser.parse(raw_job)
                parsed_jobs.append(parsed_job)

            except Exception as e:
                print(f"[PARSING ERROR] {e}")

        print(f"[PARSING] Parsed {len(parsed_jobs)} jobs")

        # -------------------------------------------------
        # Step 3 — Normalize jobs
        # -------------------------------------------------

        normalized_jobs = []

        print("[NORMALIZATION] Normalizing jobs...")

        for parsed_job in parsed_jobs:

            try:
                normalized_job = normalizer.normalize(parsed_job)
                normalized_jobs.append(normalized_job)

            except Exception as e:
                print(f"[NORMALIZATION ERROR] {e}")

        print(f"[NORMALIZATION] Normalized {len(normalized_jobs)} jobs")

        # -------------------------------------------------
        # Step 4 — AI relevance scoring
        # -------------------------------------------------

        print("[AI] Scoring jobs...")

        scored_jobs = []

        for job in normalized_jobs:

            try:
                score = scorer.score(job)

                job["relevance_score"] = score

                scored_jobs.append(job)

            except Exception as e:
                print(f"[AI ERROR] {e}")

        print(f"[AI] Scored {len(scored_jobs)} jobs")

        # -------------------------------------------------
        # Step 5 — Store in database
        # -------------------------------------------------

        print("[DATABASE] Saving jobs...")

        saved_count = 0

        for job_data in scored_jobs:

            try:

                job = Job(
                    title=job_data.get("title"),
                    company=job_data.get("company"),
                    location=job_data.get("location"),
                    url=job_data.get("url"),
                    description=job_data.get("description"),
                    relevance_score=job_data.get("relevance_score"),
                )

                session.add(job)

                saved_count += 1

            except Exception as e:
                print(f"[DATABASE ERROR] {e}")

        session.commit()

        print(f"[DATABASE] Saved {saved_count} jobs")

        # -------------------------------------------------
        # Cleanup
        # -------------------------------------------------

        session.close()

        print("[PIPELINE] Pipeline completed successfully")