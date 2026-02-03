import os
import json
import logging
import smtplib
import requests
import re
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
from playwright.sync_api import sync_playwright

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
HISTORY_FILE = 'data/job_history.json'
MERCOR_URL = 'https://mercor.com'

# --- OPTIMIZATION: Zero-Cost Filtering ---
EXCLUDED_KEYWORDS = [
    r'\bsenior\b', r'\bsr\.\b', r'\blead\b', r'\bprincipal\b', r'\bmanager\b', 
    r'\bdirector\b', r'\bhead of\b', r'\bvp\b', r'\barchitect\b',
    r'\bphd\b', r'\bmd\b', r'\bjd\b', r'\bexpert\b', r'\badvanced\b', 
    r'\bexperienced\b', r'\biii\b', r'\biv\b'
]
# Exceptions for "Manager" roles that might be entry level (though rare, good to have)
ALLOWED_EXCEPTIONS = [
    r'product manager', r'project manager', r'community manager'
]

def is_excluded_title(title: str) -> bool:
    """Return True if title contains senior/advanced keywords."""
    title_lower = title.lower()
    
    # Check for exceptions first
    for exc in ALLOWED_EXCEPTIONS:
        if re.search(exc, title_lower):
            return False
            
    # Check exclusions
    for pattern in EXCLUDED_KEYWORDS:
        if re.search(pattern, title_lower):
            logger.info(f"Skipping job '{title}' due to exclusion keyword: {pattern}")
            return True
            
    return False

# --- OPTIMIZATION: Smart Extraction ---
def optimize_description(text: str) -> str:
    """
    Condense description to save tokens.
    Priority: "Requirements/Qualifications" section.
    Fallback: First 3000 chars.
    """
    if not text:
        return ""
        
    # Text is often Markdown from JSON-LD or raw text
    # Look for headers
    headers = [
        "Requirements", "Qualifications", "What you bring", "Who you are", 
        "Ideal Candidate", "Skills", "Prerequisites"
    ]
    
    # Try to find a header
    best_start = -1
    for header in headers:
        # Check for markdown header (**Header**) or plain text
        idx = text.find(header)
        if idx != -1:
            if best_start == -1 or idx < best_start:
                best_start = idx
    
    if best_start != -1:
        # Found a relevant section!
        # Take from that section onwards, up to 3000 chars
        # Often valid info is 500 chars before (Role overview) + the requirements
        start_safe = max(0, best_start - 500) 
        optimized = text[start_safe:]
    else:
        # No header found, take the top (usually summary + bullets)
        optimized = text
        
    # Hard limit to 3000 chars (~750 tokens)
    if len(optimized) > 3000:
        optimized = optimized[:3000] + "\n...[TRUNCATED]..."
        
    return optimized

@dataclass
class Job:
    id: str
    title: str
    url: str
    description: str = ""

def load_history() -> List[str]:
    """Load the list of previously seen job IDs."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading history: {e}")
        return []

def save_history(history: List[str]):
    """Save the updated list of job IDs."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def analyze_job(job: Job, client) -> bool:
    """Use Gemini to determine if the job matches criteria."""
    if not client:
        return False
        
    prompt = f"""
    Analyze the following job description to see if it matches these strict criteria:
    
    CRITERIA:
    1. Role Type: Must be a Generalist OR General Annotation/Data Labeling role.
       - It should be suitable for a recent graduate or undergraduate.
       - It MUST NOT require specialized advanced degrees (like MD, PhD, JD) unless acceptable for a fresh grad.
       - It MUST NOT require 5+ years of specialized experience.
    2. Language: Must be English or Swahili only. No other foreign languages.
    3. Location: Remote, US-based, or Worldwide.
    
    Return ONLY a JSON object: {{"match": boolean, "reason": "short explanation"}}
    
    JOB TITLE: {job.title}
    JOB DESCRIPTION:
    {job.description[:10000]}  # Truncate to avoid token limits
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # Clean response text
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
            
        result = json.loads(text)
        
        if result.get('match'):
            logger.info(f"MATCH found: {job.title} - {result.get('reason')}")
            return True
        else:
            logger.info(f"No match: {job.title} - {result.get('reason')}")
            return False
            
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return False

def send_email(matches: List[Job]):
    """Send an email with the list of matching jobs."""
    sender_email = os.getenv('SMTP_EMAIL')
    sender_password = os.getenv('SMTP_PASSWORD')
    receiver_email = os.getenv('RECEIVER_EMAIL')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    if not (sender_email and sender_password and receiver_email):
        logger.warning("SMTP credentials not set. Skipping email.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"New Mercor Job Matches ({len(matches)})"
    
    body = "<h2>New Job Matches Found</h2><ul>"
    for job in matches:
        body += f"<li><a href='{job.url}'><b>{job.title}</b></a></li>"
    body += "</ul>"
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logger.info(f"Email sent to {receiver_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def main():
    logger.info("Starting Mercor Job Bot")
    
    # Initialize Gemini Client
    api_key = os.getenv('GEMINI_API_KEY')
    genai_client = None
    if api_key:
        try:
            from google import genai
            genai_client = genai.Client(api_key=api_key)
        except ImportError:
            logger.error("google-genai module not found.")
    else:
        logger.warning("GEMINI_API_KEY not set. Analysis will be skipped.")

    history = load_history()
    jobs = []
    
    try:
        with sync_playwright() as p:
            # Launch browser ONCE
            # Auto-detect CI environment or use HEADLESS env var
            is_ci = os.getenv('GITHUB_ACTIONS') == 'true'
            force_headless = os.getenv('HEADLESS', 'false').lower() == 'true'
            use_headless = is_ci or force_headless
            
            logger.info(f"Launching browser (Headless: {use_headless})...")
            browser = p.chromium.launch(headless=use_headless)
            context = browser.new_context(viewport={'width': 1366, 'height': 768})
            page = context.new_page()
            
            # --- PHASE 1: DISCOVERY ---
            logger.info(f"Navigating to {MERCOR_URL}...")
            try:
                page.goto("https://work.mercor.com/explore", timeout=60000)
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass # Proceed even if network is busy
            
            # Check for redirect
            if "/login" in page.url or "auth-wall" in page.url:
                logger.error("Redirected to login. Cannot scrape.")
                browser.close()
                return

            # Wait for job listings
            logger.info("Scanning for jobs...")
            try:
                page.wait_for_selector('a[href*="listingId="]', timeout=30000)
            except Exception as e:
                logger.warning(f"Timeout waiting for first job selector: {e}")

            # Pagination
            max_pages = 5
            current_page = 1
            
            while current_page <= max_pages:
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                found_count = 0
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    job_id = None
                    
                    if 'listingId=' in href:
                        match = re.search(r'listingId=(list_[\w-]+)', href)
                        if match: job_id = match.group(1)
                    elif 'jobs/list_' in href:
                        job_id = href.split('list_')[-1]
                        
                    if job_id:
                        job_url = f"https://work.mercor.com/jobs/{job_id}"
                        # Clean title
                        title = link.get_text(strip=True)
                        if "Apply" in title:
                            title = title.split("Apply")[0].strip()
                            
                        if len(title) > 100:
                            title = title[:100] + "..."
                        
                        # --- OPTIMIZATION 1: Zero-Cost Filter ---
                        if is_excluded_title(title):
                            continue

                        jobs.append(Job(id=job_id, title=title, url=job_url))
                        found_count += 1
                
                logger.info(f"Page {current_page}: Found {found_count} jobs.")
                
                # Check for Next button
                try:
                    next_btn = page.locator('button[title="Next"]')
                    if next_btn.is_visible() and next_btn.is_enabled():
                        next_btn.click()
                        page.wait_for_timeout(2000)
                        current_page += 1
                    else:
                        break
                except:
                    break
                    
            # --- PHASE 2: DETAILS & ANALYSIS ---
            # Deduplicate
            unique_jobs = {j.id: j for j in jobs}.values()
            new_jobs = [j for j in unique_jobs if j.id not in history]
            logger.info(f"Found {len(new_jobs)} new jobs to process.")
            
            matches = []
            processed_ids = []
            
            for i, job in enumerate(new_jobs):
                logger.info(f"Processing ({i+1}/{len(new_jobs)}): {job.url}")
                try:
                    # Navigate to job details using SAME page
                    page.goto(job.url, timeout=30000)
                    
                    # Faster wait strategy
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except: pass
                    
                    # --- OPTIMIZATION 2: JSON-LD Extraction ---
                    description = ""
                    try:
                        # Try to get structured data first (much cleaner/smaller)
                        json_ld_handle = page.locator('script[type="application/ld+json"]').first
                        if json_ld_handle.count() > 0:
                            json_text = json_ld_handle.text_content()
                            data = json.loads(json_text)
                            description = data.get('description', '')
                            logger.info("Extracted description from JSON-LD.")
                    except Exception as e:
                        logger.warning(f"JSON-LD extraction failed: {e}")

                    if not description:
                        # Fallback to full HTML text
                        content = page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        description = soup.get_text(separator=' ', strip=True)
                    
                    # --- OPTIMIZATION 3: Smart Truncation ---
                    job.description = optimize_description(description)
                    
                    # Analyze if client exists
                    if genai_client:
                        if analyze_job(job, genai_client):
                            matches.append(job)
                    
                    processed_ids.append(job.id)
                    
                    # Save history specifically after each success to prevent data loss
                    if len(processed_ids) % 5 == 0:
                        save_history(history + processed_ids)
                        
                except Exception as e:
                    logger.error(f"Failed to process {job.id}: {e}")
            
            # Final save
            save_history(history + processed_ids)
            browser.close()
            
            if matches:
                send_email(matches)
            else:
                logger.info("No matches found.")

    except Exception as e:
        logger.error(f"Bot crash: {e}")
    
    logger.info("Bot execution complete")

if __name__ == "__main__":
    main()
