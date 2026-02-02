import requests
import json
import re

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        res = requests.get('https://work.mercor.com/explore', headers=headers)
        res.raise_for_status()
        
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', res.text)
        if match:
            data = json.loads(match.group(1))
            build_id = data.get('buildId')
            print(f"Build ID: {build_id}")
            
            if 'props' in data and 'pageProps' in data['props']:
                page_props = data['props']['pageProps']
                print("PageProps keys:", list(page_props.keys()))
                
                # Check for React Query state
                if 'dehydratedState' in page_props:
                    print("✅ Found dehydratedState (React Query)!")
                    queries = page_props['dehydratedState'].get('queries', [])
                    print("Query Keys:", [q.get('queryKey') for q in queries])
                    
                # Robust search for "jobs"
                data_str = json.dumps(page_props)
                if "job" in data_str.lower():
                    print("Found 'job' keyword in data.")
                    # meaningful snippet
                    start = data_str.lower().find("job")
                    print("Snippet:", data_str[start:start+200])
        else:
            print("No __NEXT_DATA__ found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
