import requests

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://work.mercor.com/explore',
        'Content-Type': 'application/json'
    }
    endpoints = [
        "https://work.mercor.com/api/jobs",
        "https://work.mercor.com/api/opportunities",
        "https://work.mercor.com/api/explore",
        "https://work.mercor.com/api/trpc", # Common for T3 stack
        "https://api.mercor.com/jobs",
        "https://api.mercor.com/v1/jobs",
        "https://work.mercor.com/json/jobs.json"
    ]
    
    for url in endpoints:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            print(f"{url}: {res.status_code}")
            if res.status_code == 200:
                print(f"  Snippet: {res.text[:200]}")
        except Exception as e:
            print(f"{url}: Error {e}")

if __name__ == "__main__":
    main()
