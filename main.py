from playwright.sync_api import sync_playwright

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False,
        executable_path=BRAVE_PATH
    )

    page = browser.new_page()

    page.goto("https://google.com")

    print(page.title())

    input("Press ENTER to close...")

    browser.close()