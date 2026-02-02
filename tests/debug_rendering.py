from playwright.sync_api import sync_playwright
import time

def debug_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        url = "https://work.mercor.com/explore"
        print(f"Navigating to {url}...")
        page.goto(url, timeout=60000)
        
        # Wait arbitrary time for load
        time.sleep(10)
        
        print(f"Current URL: {page.url}")
        print(f"Page Title: {page.title()}")
        
        # Check for specific texts
        content = page.content()
        if "Log in" in content or "Sign up" in content:
            print("⚠️ Trace of Login/Signup found in content.")
        if "Generalist" in content:
            print("✅ 'Generalist' found in content.")
        
        # Dump all links
        links = page.eval_on_selector_all("a", "elements => elements.map(e => ({href: e.href, text: e.innerText}))")
        print(f"\nFound {len(links)} links. First 10:")
        for link in links[:10]:
            print(f"- {link['text'][:20]}: {link['href']}")
            
        browser.close()

if __name__ == "__main__":
    debug_page()
