from googlesearch import search

def main():
    query = 'site:mercor.com "Generalist Writer"'
    print(f"Searching for: {query}")
    
    try:
        # Search for top 10 results
        results = search(query, num_results=10)
        found = False
        for url in results:
            print(f"Found: {url}")
            if "mercor.com" in url:
                found = True
        
        if not found:
            print("No results found for mercor.com")
            
        # Try broader search
        query2 = 'site:work.mercor.com "Generalist"'
        print(f"\nSearching for: {query2}")
        results2 = search(query2, num_results=10)
        for url in results2:
             print(f"Found: {url}")

    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    main()
