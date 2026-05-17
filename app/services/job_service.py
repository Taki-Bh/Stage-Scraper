# app/services/job_service.py

from app.scraping.linkedin_scraper import LinkedInScraper
"""from app.extraction.parser import JobParser
from app.extraction.normalizer import JobNormalizer
from app.ai.relevance import RelevanceScorer
from app.database.session import get_db_session
from app.database.models import Job"""



def run_pipeline() -> None:
    """
    Main orchestration pipeline.

    Flow:
        Scrape -> Parse -> Normalize -> Score -> Store
    """

    print("[PIPELINE] Starting pipeline...")

    # -------------------------------------------------
    # Initialize components
    # -------------------------------------------------

    scraper = LinkedInScraper()

    #parser = JobParser()

    #normalizer = JobNormalizer()

    #scorer = RelevanceScorer()

    #session = get_db_session()

    # -------------------------------------------------
    # Step 1 — Scrape raw jobs
    # -------------------------------------------------

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