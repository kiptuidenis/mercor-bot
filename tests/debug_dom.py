from playwright.sync_api import sync_playwright
import time

def debug_dom():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        url = "https://work.mercor.com/explore"
        print(f"Navigating to {url}...")
        page.goto(url)
        
        print("\n⚠️  PLEASE CHECK THE BROWSER WINDOW ⚠️")
        print("Do you see job listings? (y/n)")
        # Wait for user visual verification could be useful, 
        # but let's just wait a bit and dump.
        time.sleep(10) 
        
        print("Dumping all links on the page...")
        links = page.query_selector_all("a")
        
        with open("page_links_dump.txt", "w", encoding="utf-8") as f:
            f.write(f"Total links found: {len(links)}\n")
            for i, link in enumerate(links):
                txt = link.inner_text().replace('\n', ' ').strip()
                href = link.get_attribute("href")
                line = f"{i}: Text='{txt}' Href='{href}'"
                print(line)
                f.write(line + "\n")
        
        print("\nDump saved to page_links_dump.txt")
        browser.close()

if __name__ == "__main__":
    debug_dom()
