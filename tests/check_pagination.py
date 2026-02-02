import requests
from bs4 import BeautifulSoup

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = "https://work.mercor.com/explore"
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Look for pagination elements
        navs = soup.find_all('nav')
        print(f"Found {len(navs)} nav elements")
        
        buttons = soup.find_all('button')
        pagination_buttons = [b.get_text() for b in buttons if any(x in b.get_text().lower() for x in ['next', 'previous', 'page', '1', '2'])]
        print("Potential pagination buttons:", pagination_buttons)
        
        links = soup.find_all('a')
        pagination_links = [a.get_text() for a in links if a.get_text().isdigit()]
        print("Numeric links (pages?):", pagination_links)

        # Check for "Next" link
        next_links = [a for a in links if 'next' in a.get_text().lower()]
        if next_links:
            print("Found 'Next' links:", [l.get('href') for l in next_links])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
