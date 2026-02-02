import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get('https://work.mercor.com/explore', headers=headers)
print(response.text[:20000]) # Print first 20k chars to look for scripts/data
