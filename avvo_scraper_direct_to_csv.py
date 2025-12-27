#!/usr/bin/env python3
"""
Avvo Profile Scraper - Direct to CSV
Combines scraping and CSV conversion into one step
No HTML files are saved - goes directly from scraping to CSV
"""

import undetected_chromedriver as uc
import time
import re
import json
import csv
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import extraction and save functions from html_to_csv_converter
try:
    from html_to_csv_converter import extract_profile_data_from_html, save_to_csv
except ImportError:
    print("❌ Error: Could not import from html_to_csv_converter.py")
    print("   Make sure html_to_csv_converter.py is in the same directory")
    sys.exit(1)

# Configuration
# URLs file - one URL per line
URLS_FILE = "urls.txt"  # File containing URLs to scrape

# Days back filter - only get reviews from last N days (None = no filter, get all reviews)
# Default value if not specified in urls.txt or command line
DAYS_BACK_DEFAULT = 365  # Default: 365 days

# Output CSV filename
OUTPUT_CSV = "Avvo_Scraping_data_output.csv"

def parse_review_date(date_str):
    """Parse review date from various formats. Returns datetime object or None."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    date_formats = [
        '%B %d, %Y',      # February 1, 2018
        '%b %d, %Y',      # Feb 1, 2018
        '%m/%d/%Y',       # 02/01/2018
        '%B %d,%Y',       # February 1,2018 (no space)
        '%Y-%m-%d',       # 2018-02-01
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    return None


def extract_review_date_from_html(review_html):
    """Extract date from a review HTML element."""
    soup = BeautifulSoup(review_html, 'html.parser')
    header = soup.find('div', class_='client-review-header')
    if header:
        # Remove tooltip
        for tooltip in header.find_all(['div'], class_=re.compile(r'tooltip')):
            tooltip.decompose()
        
        first_para = header.find('p')
        if first_para:
            para_text = first_para.get_text(separator=' ', strip=True)
            para_text = re.sub(r'\s+', ' ', para_text)
            
            match = re.search(r'Posted by .+?\s*\|\s*(.+?)(?:\s*\|)?$', para_text)
            if match:
                date_str = match.group(1).strip()
                date_str = re.sub(r'\s*\|\s*.*$', '', date_str).strip()
                return parse_review_date(date_str)
    return None


def read_urls_from_file(file_path):
    """
    Read URLs from a text file (one URL per line)
    Also reads DAYS_BACK configuration if specified in the file
    
    Args:
        file_path: Path to the file containing URLs
    
    Returns:
        Tuple of (list of URLs, days_back value or None)
    """
    urls = []
    days_back = None
    
    if not os.path.exists(file_path):
        print(f"⚠️  URLs file '{file_path}' not found. Creating sample file...")
        # Create a sample file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Add one URL per line\n")
            f.write("# Lines starting with # are ignored\n")
            f.write("# Optional: Add DAYS_BACK=365 to set review date filter (default: 365 days)\n")
            f.write("# DAYS_BACK=365\n")
            f.write("https://www.avvo.com/attorneys/28204-nc-michael-demayo-1742166.html\n")
        print(f"✅ Created sample file: {file_path}")
        print(f"   Please add your URLs to this file and run again.\n")
        return [], None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Check for DAYS_BACK configuration (can be with or without #)
            if line.upper().startswith('DAYS_BACK=') or (line.startswith('#') and 'DAYS_BACK=' in line.upper()):
                # Extract DAYS_BACK value
                # Handle both "DAYS_BACK=365" and "# DAYS_BACK=365"
                if line.startswith('#'):
                    # Remove # and any leading whitespace
                    line = line[1:].strip()
                
                if '=' in line:
                    try:
                        days_back_str = line.split('=', 1)[1].strip()
                        # Handle "none" or "None" to disable filter
                        if days_back_str.lower() == 'none':
                            days_back = None
                        else:
                            days_back = int(days_back_str)
                        print(f"📅 Found DAYS_BACK={days_back} in {file_path}")
                    except ValueError:
                        print(f"⚠️  Invalid DAYS_BACK value on line {line_num}: {line}")
                continue
            
            # Skip empty lines and comments (but we already handled DAYS_BACK comments above)
            if not line or (line.startswith('#') and 'DAYS_BACK=' not in line.upper()):
                continue
            
            # Validate URL
            if line.startswith('http://') or line.startswith('https://'):
                urls.append(line)
            else:
                print(f"⚠️  Skipping invalid URL on line {line_num}: {line}")
    
    return urls, days_back


def save_to_csv_append(data, reviews, output_csv_path, is_first_url=False):
    """
    Save extracted data and reviews to CSV file (append mode with blank line between URLs)
    
    Args:
        data: Dictionary with profile data
        reviews: List of review dictionaries
        output_csv_path: Path to output CSV file
        is_first_url: If True, write header. If False, append without header.
    """
    # Create rows - one row per review with all profile data
    rows = []
    
    # If there are reviews, create one row per review with all profile data
    if reviews:
        for review in reviews:
            row = data.copy()
            # Add review-specific fields to each row
            row['reviewer_name'] = review.get('reviewer_name')
            row['review_date'] = review.get('review_date')
            row['review_rating'] = review.get('review_rating')
            row['review_title'] = review.get('review_title')
            row['review_text'] = review.get('review_text')
            row['review_type'] = review.get('review_type')
            row['review_tooltip'] = review.get('review_tooltip')
            # Add attorney response fields
            row['attorney_response_name'] = review.get('attorney_response_name')
            row['attorney_response_date'] = review.get('attorney_response_date')
            row['attorney_response_text'] = review.get('attorney_response_text')
            rows.append(row)
    else:
        # No reviews - just one row with profile data and empty review fields
        row = data.copy()
        row['reviewer_name'] = None
        row['review_date'] = None
        row['review_rating'] = None
        row['review_title'] = None
        row['review_text'] = None
        row['review_type'] = None
        row['review_tooltip'] = None
        row['attorney_response_name'] = None
        row['attorney_response_date'] = None
        row['attorney_response_text'] = None
        rows.append(row)
    
    # Clean text fields - replace newlines with spaces to prevent CSV row breaks
    text_fields = ['review_text', 'review_title', 'attorney_response_text', 'biography', 'company_address', 
                    'education', 'bar_admissions', 'honors_awards', 'associations', 
                    'work_experience', 'practice_areas', 'additional_practice_areas',
                    'practice_area_percentages', 'cost_details', 'retainer_info',
                    'payment_methods', 'license_details']
    
    for row in rows:
        for field in text_fields:
            if field in row and row[field] is not None:
                # Replace newlines and carriage returns with spaces
                row[field] = str(row[field]).replace('\n', ' ').replace('\r', ' ')
                # Clean up multiple spaces
                row[field] = re.sub(r'\s+', ' ', row[field]).strip()
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Append mode: if file exists and not first URL, append without header
    if os.path.exists(output_csv_path) and not is_first_url:
        # Append mode - add blank row first (empty row with all columns)
        # Read existing CSV to get column names
        existing_df = pd.read_csv(output_csv_path, nrows=0)  # Read only header
        blank_row = pd.DataFrame([{col: '' for col in existing_df.columns}])
        blank_row.to_csv(output_csv_path, mode='a', index=False, header=False, encoding='utf-8', quoting=csv.QUOTE_MINIMAL)
        # Now append the actual data
        df.to_csv(output_csv_path, mode='a', index=False, header=False, encoding='utf-8', quoting=csv.QUOTE_MINIMAL)
    else:
        # Write mode - create new file with header
        df.to_csv(output_csv_path, index=False, encoding='utf-8', quoting=csv.QUOTE_MINIMAL)
    
    # Display review count
    if reviews:
        print(f"✅ Added {len(rows)} rows ({len(reviews)} reviews + profile data in each row)")
    else:
        print(f"✅ Added 1 row (profile data, no reviews)")
    
    return True


def scrape_and_convert_to_csv(url, days_back=None, save_html=False):
    """
    Scrape Avvo profile and save directly to CSV
    
    Args:
        url: Avvo profile URL
        days_back: Number of days back to filter reviews (None = all reviews)
        save_html: If True, also save HTML file (default: False)
    
    Returns:
        Path to CSV file or None if failed
    """
    driver = None
    try:
        # Calculate cutoff date if days_back filter is set
        cutoff_date = None
        filter_info = ""
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            filter_info = f" | Review Date Filter: Last {days_back} days (from {cutoff_date.strftime('%Y-%m-%d')})"
            print(f"📅 Date filter: Only getting reviews from last {days_back} days")
            print(f"   Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
        else:
            filter_info = " | Review Date Filter: All reviews (no date filter)"
            print("📅 No date filter: Getting all reviews")
        
        print("\n" + "="*80)
        print(f"AVVO PROFILE SCRAPER - DIRECT TO CSV{filter_info}")
        print("="*80)
        print(f"Starting undetected Chrome browser...")
        
        # Create options
        options = uc.ChromeOptions()
        # options.add_argument('--headless=new')  # Uncomment for headless mode
        
        # Initialize undetected Chrome driver
        driver = uc.Chrome(options=options)
        
        print(f"\n🌐 Navigating to: {url}")
        driver.get(url)
        
        print("⏳ Waiting for page to load and Cloudflare to complete...")
        
        # Wait for Cloudflare challenge to complete - use more efficient wait
        wait = WebDriverWait(driver, 20)  # Reduced from 30 to 20 seconds
        
        # Wait for either Cloudflare to pass OR profile name to appear (whichever comes first)
        try:
            # First check if Cloudflare challenge is present
            if "Just a moment" in driver.title:
                # Wait for Cloudflare to complete
                wait.until(lambda d: "Just a moment" not in d.title)
                print("✅ Cloudflare challenge completed!")
                time.sleep(1)  # Reduced from 2 to 1 second
            else:
                print("✅ No Cloudflare challenge detected")
            
            # Now wait for actual page content (profile name) - this is more reliable
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.profile-name")))
            print("✅ Page loaded successfully!")
            
        except Exception as e:
            print("⚠️  Waiting for page elements...")
            # Fallback: just wait a bit and continue
            time.sleep(2)
        
        # Try to find profile name to confirm page loaded
        try:
            profile_name = driver.find_element(By.CSS_SELECTOR, "h1.profile-name")
            print(f"✅ Profile found: {profile_name.text}")
        except:
            print("⚠️  Could not find profile name element (continuing anyway)")
        
        # Get the main page source
        html_content = driver.page_source
        main_soup = BeautifulSoup(html_content, 'html.parser')
        
        # Filter main page reviews if date filter is enabled
        should_stop_main = False
        if cutoff_date:
            print("\n📅 Filtering reviews from main page...")
            main_reviews = main_soup.find_all('div', class_='client-review')
            filtered_count = 0
            
            for review in main_reviews:
                review_date = extract_review_date_from_html(str(review))
                if review_date:
                    if review_date < cutoff_date:
                        # Review is too old - remove it and stop checking
                        review.decompose()
                        filtered_count += 1
                        should_stop_main = True
                        print(f"   ⚠️  Found review older than {days_back} days on main page ({review_date.strftime('%Y-%m-%d')})")
                        break
                # If date couldn't be parsed, keep the review to be safe
            
            if should_stop_main:
                print(f"   ✅ Filtered main page - stopping pagination (found old review)")
            elif filtered_count > 0:
                print(f"   ✅ Filtered {filtered_count} old review(s) from main page")
            else:
                print(f"   ✅ All {len(main_reviews)} reviews on main page are within date range")
        
        # Check for review pagination - find all review page links
        print("\n🔍 Checking for review pagination...")
        
        # Extract base URL (without query parameters)
        base_url = url.split('?')[0]
        review_page_urls = set()
        
        # Method 1: Look for pagination links in the page
        pagination_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='page=']")
        for link in pagination_links:
            href = link.get_attribute('href')
            if href and 'page=' in href:
                # Extract page number
                page_match = re.search(r'page=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    # Normalize URL
                    if href.startswith('/'):
                        href = 'https://www.avvo.com' + href
                    elif not href.startswith('http'):
                        href = base_url + '?page=' + str(page_num)
                    review_page_urls.add((page_num, href))
        
        # Method 2: Check for "Next" button or page numbers in reviews section
        try:
            # Look for pagination controls
            pagination_elements = driver.find_elements(By.CSS_SELECTOR, ".pagination a, .page-numbers a, [class*='pagination'] a")
            for elem in pagination_elements:
                href = elem.get_attribute('href')
                text = elem.text.strip()
                if href and ('page=' in href or text.isdigit()):
                    if 'page=' in href:
                        page_match = re.search(r'page=(\d+)', href)
                    elif text.isdigit():
                        page_num = int(text)
                        href = base_url + f"?page={page_num}"
                        page_match = (page_num,)
                    else:
                        continue
                    
                    if page_match:
                        page_num = int(page_match.group(1) if isinstance(page_match, re.Match) else page_match[0])
                        if not href.startswith('http'):
                            href = base_url + f"?page={page_num}"
                        review_page_urls.add((page_num, href))
        except:
            pass
        
        # Method 3: Try to find max page number from pagination text
        try:
            pagination_text = driver.find_elements(By.XPATH, "//*[contains(text(), 'Page') or contains(text(), 'of')]")
            for elem in pagination_text:
                text = elem.text
                # Look for patterns like "Page 1 of 5" or "1 of 5"
                match = re.search(r'(?:Page\s+)?\d+\s+of\s+(\d+)', text, re.IGNORECASE)
                if match:
                    max_page = int(match.group(1))
                    # Generate URLs for all pages
                    for page_num in range(2, max_page + 1):  # Start from 2 (page 1 is already loaded)
                        page_url = base_url + f"?page={page_num}"
                        review_page_urls.add((page_num, page_url))
                    break
        except:
            pass
        
        # Sort by page number and filter out page 1 (already loaded)
        review_page_urls = sorted([(p, u) for p, u in review_page_urls if p > 1], key=lambda x: x[0])
        
        if review_page_urls:
            print(f"✅ Found {len(review_page_urls)} additional review page(s)")
            for page_num, page_url in review_page_urls:
                print(f"   - Page {page_num}: {page_url}")
        else:
            print("   No additional review pages found")
        
        # Load all review pages
        all_reviews_html = []
        pages_loaded_count = 1
        
        if cutoff_date and should_stop_main:
            print(f"\n⏭️  Skipping pagination - found old review on main page")
            review_page_urls = []
        
        if review_page_urls:
            print(f"\n📄 Loading additional review pages...")
            for page_num, page_url in review_page_urls:
                if cutoff_date and should_stop_main:
                    break
                
                print(f"   Loading page {page_num}...")
                try:
                    driver.get(page_url)
                    time.sleep(1)  # Reduced from 2 to 1 second
                    
                    # Wait for Cloudflare if needed (quick check)
                    if "Just a moment" in driver.title:
                        try:
                            WebDriverWait(driver, 5).until(lambda d: "Just a moment" not in d.title)
                        except:
                            pass  # Continue anyway
                    
                    page_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    review_containers = page_soup.find_all('div', class_='client-review')
                    
                    if review_containers:
                        reviews_added = 0
                        should_stop = False
                        
                        # Check reviews one by one - stop immediately when we find an old one
                        for review in review_containers:
                            review_html = str(review)
                            
                            # Check date if filter is enabled
                            if cutoff_date:
                                review_date = extract_review_date_from_html(review_html)
                                
                                if review_date:
                                    if review_date < cutoff_date:
                                        # Review is too old - STOP IMMEDIATELY, don't check remaining reviews
                                        print(f"      ⚠️  Found review older than {days_back} days ({review_date.strftime('%Y-%m-%d')}) - stopping immediately")
                                        should_stop = True
                                        break  # Exit review loop immediately
                                    else:
                                        # Review is within date range - add it
                                        all_reviews_html.append(review_html)
                                        reviews_added += 1
                                else:
                                    # Couldn't parse date - include it to be safe
                                    all_reviews_html.append(review_html)
                                    reviews_added += 1
                            else:
                                # No date filter - add all reviews
                                all_reviews_html.append(review_html)
                                reviews_added += 1
                            
                            # If we found an old review, stop checking remaining reviews on this page
                            if should_stop:
                                break
                        
                        if reviews_added > 0 and not should_stop:
                            print(f"      ✅ Found {len(review_containers)} reviews, added {reviews_added} (within date range)")
                            pages_loaded_count += 1
                        elif should_stop:
                            print(f"      ⏹️  Stopped after checking {reviews_added + 1} review(s) - found old review")
                        
                        # Stop loading more pages if we found an old review
                        if should_stop:
                            should_stop_main = True
                            break  # Exit page loop - don't load next page
                    else:
                        print(f"      ⚠️  No reviews found on page {page_num} - stopping")
                        break
                        
                except Exception as e:
                    print(f"      ❌ Error loading page {page_num}: {e}")
                    break
        
        # If we didn't find all pages upfront, try iterative approach
        if not review_page_urls and not should_stop_main:
            print(f"\n📄 Trying iterative approach to find all review pages...")
            page_num = 2
            consecutive_empty_pages = 0
            max_empty_pages = 2
            
            while consecutive_empty_pages < max_empty_pages:
                page_url = base_url + f"?page={page_num}"
                print(f"   Trying page {page_num}...")
                
                try:
                    driver.get(page_url)
                    time.sleep(1)  # Reduced from 2 to 1 second
                    
                    # Wait for Cloudflare if needed (quick check)
                    if "Just a moment" in driver.title:
                        try:
                            WebDriverWait(driver, 5).until(lambda d: "Just a moment" not in d.title)
                        except:
                            pass  # Continue anyway
                    
                    page_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    review_containers = page_soup.find_all('div', class_='client-review')
                    
                    if review_containers:
                        reviews_added = 0
                        should_stop = False
                        
                        # Check reviews one by one - stop immediately when we find an old one
                        for review in review_containers:
                            review_html = str(review)
                            
                            # Check date if filter is enabled
                            if cutoff_date:
                                review_date = extract_review_date_from_html(review_html)
                                
                                if review_date:
                                    if review_date < cutoff_date:
                                        # Review is too old - STOP IMMEDIATELY, don't check remaining reviews
                                        print(f"      ⚠️  Found review older than {days_back} days ({review_date.strftime('%Y-%m-%d')}) - stopping immediately")
                                        should_stop = True
                                        break  # Exit review loop immediately
                                    else:
                                        # Review is within date range - add it
                                        all_reviews_html.append(review_html)
                                        reviews_added += 1
                                else:
                                    # Couldn't parse date - include it to be safe
                                    all_reviews_html.append(review_html)
                                    reviews_added += 1
                            else:
                                # No date filter - add all reviews
                                all_reviews_html.append(review_html)
                                reviews_added += 1
                            
                            # If we found an old review, stop checking remaining reviews on this page
                            if should_stop:
                                break
                        
                        if reviews_added > 0 and not should_stop:
                            print(f"      ✅ Found {len(review_containers)} reviews, added {reviews_added} (within date range)")
                            consecutive_empty_pages = 0  # Reset counter
                            pages_loaded_count += 1
                        elif should_stop:
                            print(f"      ⏹️  Stopped after checking {reviews_added + 1} review(s) - found old review")
                        
                        # Stop loading more pages if we found an old review
                        if should_stop:
                            print(f"      ✅ Reached date limit - stopping pagination")
                            should_stop_main = True
                            break  # Exit while loop - don't try next page
                        
                        page_num += 1
                    else:
                        # Check for "no reviews" message or similar
                        page_text = page_soup.get_text().lower()
                        if 'no reviews' in page_text or 'no more reviews' in page_text:
                            print(f"      ℹ️  Page {page_num} indicates no more reviews - stopping")
                            break
                        
                        consecutive_empty_pages += 1
                        print(f"      ⚠️  No reviews found on page {page_num} ({consecutive_empty_pages}/{max_empty_pages})")
                        
                        if consecutive_empty_pages >= max_empty_pages:
                            print(f"      ✅ Reached end of reviews (no reviews for {max_empty_pages} consecutive pages)")
                            break
                        
                        page_num += 1
                        
                except Exception as e:
                    print(f"      ❌ Error loading page {page_num}: {e}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_empty_pages:
                        break
                    page_num += 1
        
        # Combine all reviews into main HTML
        if all_reviews_html:
            print(f"\n📝 Combining {len(all_reviews_html)} additional reviews into HTML...")
            
            # Find the reviews container in main HTML - try multiple selectors
            reviews_section = None
            
            # Try different ways to find the reviews container
            selectors = [
                ('div', {'class': 'reviews'}),
                ('div', {'class': lambda x: x and 'review' in x.lower()}),
                ('section', {'class': 'review-section'}),
                ('div', {'id': 'reviews'}),
                ('div', {'class': 'review-body'}),
            ]
            
            for tag, attrs in selectors:
                reviews_section = main_soup.find(tag, attrs)
                if reviews_section:
                    break
            
            # If still not found, look for any div containing client-review
            if not reviews_section:
                existing_reviews = main_soup.find_all('div', class_='client-review')
                if existing_reviews:
                    # Find parent container of existing reviews
                    reviews_section = existing_reviews[0].find_parent('div', class_=lambda x: x and ('review' in str(x).lower() or 'reviews' in str(x).lower()))
            
            if reviews_section:
                # Append all additional reviews
                for review_html in all_reviews_html:
                    review_soup = BeautifulSoup(review_html, 'html.parser')
                    review_div = review_soup.find('div', class_='client-review')
                    if review_div:
                        reviews_section.append(review_div)
                
                # Update the HTML content
                html_content = str(main_soup)
                print(f"   ✅ Combined all reviews into HTML")
            else:
                # If we can't find the container, append to body as fallback
                print(f"   ⚠️  Could not find reviews section, appending to body")
                body = main_soup.find('body')
                if body:
                    for review_html in all_reviews_html:
                        review_soup = BeautifulSoup(review_html, 'html.parser')
                        body.append(review_soup)
                    html_content = str(main_soup)
                else:
                    html_content = driver.page_source
        
        # Get final HTML content (use main page if no additional reviews)
        if not all_reviews_html:
            html_content = driver.page_source
        
        # Final pass: Filter out old reviews from the final HTML if date filter is enabled
        if cutoff_date:
            print(f"\n🔍 Final filtering pass: Removing reviews older than {days_back} days...")
            final_soup = BeautifulSoup(html_content, 'html.parser')
            all_reviews = final_soup.find_all('div', class_='client-review')
            removed_count = 0
            
            for review in all_reviews:
                review_date = extract_review_date_from_html(str(review))
                if review_date:
                    if review_date < cutoff_date:
                        # Review is too old - remove it
                        review.decompose()
                        removed_count += 1
            
            if removed_count > 0:
                print(f"   ✅ Removed {removed_count} old review(s) from final HTML")
                html_content = str(final_soup)
            else:
                print(f"   ✅ All reviews are within date range")
        
        # Extract user ID for filename
        match = re.search(r'/attorneys/([^/]+)\.html', base_url)
        if match:
            user_id = match.group(1)
        else:
            user_id = "unknown"
        
        # Optionally save HTML (for debugging)
        if save_html:
            html_filename = f"{user_id}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"💾 HTML saved to: {html_filename}")
        
        # Count total reviews in final HTML
        final_soup = BeautifulSoup(html_content, 'html.parser')
        total_reviews = len(final_soup.find_all('div', class_='client-review'))
        
        # Extract data directly from HTML
        print(f"\n📊 Extracting data from HTML...")
        # Create filter info string for CSV
        csv_filter_info = None
        if days_back:
            csv_filter_info = f"Last {days_back} days (from {cutoff_date.strftime('%Y-%m-%d')})"
        else:
            csv_filter_info = "All reviews (no date filter)"
        
        data, reviews = extract_profile_data_from_html(html_content, review_date_filter=csv_filter_info)
        
        if not data:
            print("❌ Failed to extract data")
            return None
        
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        print(f"Page title: {driver.title}")
        print(f"Main page URL: {url}")
        print(f"Total review pages loaded: {pages_loaded_count}")
        print(f"Total reviews found: {total_reviews}")
        print(f"Total reviews extracted: {len(reviews)}")
        print(f"HTML length: {len(html_content)} characters")
        
        # Close browser
        driver.quit()
        print("\n✅ Browser closed successfully")
        
        # Return data and reviews instead of saving here
        return (data, reviews)
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        if driver:
            try:
                driver.quit()
            except:
                pass
        return None


if __name__ == "__main__":
    print("\n" + "="*80)
    print("AVVO PROFILE SCRAPER - BATCH PROCESSING")
    print("="*80)
    
    # Read URLs and DAYS_BACK from file
    urls, days_back_from_file = read_urls_from_file(URLS_FILE)
    
    if not urls:
        print("❌ No URLs found. Please add URLs to the file and try again.")
        sys.exit(1)
    
    print(f"\n📋 Found {len(urls)} URL(s) to process:")
    for i, url in enumerate(urls, 1):
        print(f"   {i}. {url}")
    
    # Determine DAYS_BACK: command line > file > default
    DAYS_BACK = DAYS_BACK_DEFAULT  # Start with default
    
    if days_back_from_file is not None:
        DAYS_BACK = days_back_from_file
        print(f"\n📅 Using DAYS_BACK from {URLS_FILE}: {DAYS_BACK}")
    else:
        print(f"\n📅 Using default DAYS_BACK: {DAYS_BACK} (not specified in {URLS_FILE})")
    
    # Override DAYS_BACK from command line if provided (highest priority)
    if len(sys.argv) > 1:
        DAYS_BACK = int(sys.argv[1]) if sys.argv[1].lower() != 'none' else None
        print(f"📅 Overriding with command line DAYS_BACK: {DAYS_BACK}")
    
    print(f"\n{'='*80}")
    print(f"Starting batch processing of {len(urls)} URL(s)...")
    print(f"{'='*80}\n")
    
    successful = 0
    failed = 0
    is_first_url = True
    
    for i, url in enumerate(urls, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(urls)}] Processing URL: {url}")
        print(f"{'='*80}")
        
        try:
            result = scrape_and_convert_to_csv(url, DAYS_BACK, save_html=False)
            
            if result:
                data, reviews = result
                # Save to CSV (append mode)
                print(f"\n💾 Saving to CSV: {OUTPUT_CSV}")
                save_to_csv_append(data, reviews, OUTPUT_CSV, is_first_url=is_first_url)
                is_first_url = False
                successful += 1
                print(f"✅ Successfully processed URL {i}/{len(urls)}")
            else:
                failed += 1
                print(f"❌ Failed to process URL {i}/{len(urls)}")
        
        except Exception as e:
            failed += 1
            print(f"❌ Error processing URL {i}/{len(urls)}: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    print("\n" + "="*80)
    print("BATCH PROCESSING SUMMARY")
    print("="*80)
    print(f"✅ Successfully processed: {successful} URL(s)")
    if failed > 0:
        print(f"❌ Failed: {failed} URL(s)")
    print(f"📄 Output CSV: {OUTPUT_CSV}")
    print("="*80 + "\n")

