from playwright.sync_api import sync_playwright
from app.core.config import *
from app.services.job_service import *
if __name__ == "__main__" :
    run_pipeline()

"""with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir=CONFIG["USER-DATA"],
        executable_path=CONFIG["PATH"],
        headless=False,
        args=[
            f"--profile-directory={PROFILE}"
        ]
    )

    page = context.new_page()

    page.goto("https://linkedin.com")

    input("Press ENTER to close...")"""