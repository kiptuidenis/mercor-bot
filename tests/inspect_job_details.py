from playwright.sync_api import sync_playwright
import time

def dump_job_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        # Using a known job URL from previous logs
        url = "https://work.mercor.com/jobs/list_AAABm4Xm5vZiwyWXybFBRJJN" 
        print(f"Navigating to {url}...")
        page.goto(url)
        print("Waiting for load...")
        time.sleep(10) # ample time for React to render
        
        html = page.content()
        with open("job_details_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Dumped HTML to job_details_dump.html")
        browser.close()

if __name__ == "__main__":
    dump_job_html()
