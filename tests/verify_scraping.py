import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.bot import fetch_latest_jobs, get_job_details

def test_scraping():
    print("Fetching jobs from mercor.com...")
    jobs = fetch_latest_jobs()
    
    if not jobs:
        print("❌ No jobs found. Selectors might be broken.")
        return
    
    print(f"✅ Found {len(jobs)} jobs.")
    
    # Test details for the first job
    first_job = jobs[0]
    print(f"Testing detail fetch for: {first_job.title} ({first_job.url})")
    
    full_job = get_job_details(first_job)
    
    if full_job.description:
        print(f"✅ Successfully fetched description ({len(full_job.description)} chars).")
        print("Snippet:", full_job.description[:200])
    else:
        print("❌ Failed to fetch description (empty).")

if __name__ == "__main__":
    test_scraping()
