import requests

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://work.mercor.com/',
        'Origin': 'https://work.mercor.com',
        'Accept': 'application/json, text/plain, */*'
    }
    
    endpoint = "/listings-explore-page"
    bases = [
        "https://work.mercor.com/api",
        "https://api.mercor.com",
        "https://api.mercor.com/v1",
        "https://work.mercor.com",
        "https://mercor.com/api"
    ]
    
    for base in bases:
        url = f"{base}{endpoint}"
        try:
            print(f"Testing {url}...")
            res = requests.get(url, headers=headers, timeout=5)
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                print(f"✅ Found! Snippet: {res.text[:200]}")
                break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
