from playwright.sync_api import sync_playwright

def test_frontend_ws(page):
    page.goto("http://localhost:3000")
    page.wait_for_timeout(2000)
    page.screenshot(path="frontend_screenshot.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_frontend_ws(page)
        finally:
            browser.close()
