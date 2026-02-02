import requests
import json

def main():
    build_id = "rIH1ZT3uTbfTH69yVO"
    url = f"https://work.mercor.com/_next/data/{build_id}/explore.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://work.mercor.com/explore',
        'Accept': '*/*'
    }
    
    # Try fetching page 2 to see the structure
    params = {'page': 2}
    print(f"Fetching {url} with params {params}...")
    try:
        res = requests.get(url, params=params, headers=headers)
        res.raise_for_status()
        data = res.json()
        
        print("Keys in response:", list(data.keys()))
        if 'pageProps' in data:
            print("PageProps keys:", list(data['pageProps'].keys()))
            # Look for job lists
            # Recursively search for "Generalist" string in the json to find where jobs are hidden
            data_str = json.dumps(data)
            if "Generalist Writer" in data_str:
                print("✅ Found 'Generalist Writer' within the data!")
            else:
                print("❌ 'Generalist Writer' NOT found in page 2 data.")
                
            # Print a snippet of where jobs might be
            # Usually in pageProps -> fallback / dehydration state / or just 'jobs'
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
