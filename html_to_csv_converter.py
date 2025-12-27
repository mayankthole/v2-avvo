"""
HTML to CSV Converter for Avvo Profile Pages
Extracts attorney profile information from HTML and saves to CSV
"""
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import sys
import os
import json
import csv


def extract_profile_data_from_html(html_content):
    """
    Extract all profile data from Avvo HTML content (string)
    
    Args:
        html_content: HTML content as string
        
    Returns:
        Tuple of (data dictionary, reviews list)
    """
    # Use html.parser (built-in) instead of lxml
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Continue with extraction logic (same as below)
    return _extract_data_from_soup(soup)


def extract_profile_data(html_file_path):
    """
    Extract all profile data from Avvo HTML file
    
    Args:
        html_file_path: Path to the HTML file
        
    Returns:
        Tuple of (data dictionary, reviews list)
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: File '{html_file_path}' not found!")
        return None, []
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None, []
    
    return extract_profile_data_from_html(html_content)


def extract_profile_data_from_html(html_content, review_date_filter=None):
    """
    Extract all profile data from Avvo HTML content (string)
    
    Args:
        html_content: HTML content as string
        review_date_filter: Optional string describing the review date filter applied (e.g., "Last 365 days (from 2024-12-27)" or "All reviews (no date filter)")
        
    Returns:
        Tuple of (data dictionary, reviews list)
    """
    # Use html.parser (built-in) instead of lxml
    soup = BeautifulSoup(html_content, 'html.parser')
    return _extract_data_from_soup(soup, review_date_filter)


def _extract_data_from_soup(soup, review_date_filter=None):
    """
    Internal function to extract data from BeautifulSoup object
    
    Args:
        soup: BeautifulSoup object
        review_date_filter: Optional string describing the review date filter applied
    """
    
    # Initialize data structure
    data = {
        'attorney_full_name': None,
        'profile_url': None,
        'firm_name': None,
        'company_address': None,
        'company_city': None,
        'company_state': None,
        'company_zip': None,
        'company_country': 'United States',
        'company_phone_number': None,
        'company_fax_number': None,
        'company_website': None,  # Actual business website URL
        'overall_average_rating': None,
        'total_review_count': 0,
        'avvo_reviews_count': 0,
        'lawyers_com_reviews_count': 0,
        'avvo_rating': None,
        'avvo_rating_description': None,
        'years_licensed': None,
        'year_licensed': None,
        'years_licensed_text': None,  # Full text: "Licensed for 35 years"
        'practice_areas': None,
        'primary_practice_area': None,
        'lawyer_at_location': None,  # e.g., "Immigration Lawyer at San Mateo, CA"
        'languages_spoken': None,
        'is_pro': False,
        'is_claimed': False,
        'free_consultation': False,
        'virtual_consultation_available': False,  # Virtual Consultation Available
        'contingency_fee': None,
        'hourly_rate': None,
        'retainer_info': None,  # Retainer information
        'cost_details': None,  # Cost section details
        'payment_methods': None,  # Payment methods (Check, Credit Card, etc.)
        'currencies_accepted': None,  # USD, etc.
        'education': None,
        'bar_admissions': None,
        'license_details': None,  # Detailed license information
        'send_message_link': None,  # Link to send message
        'google_map_directions_link': None,  # Google Maps directions link
        'profile_photo_url': None,  # Profile photo/image URL
        'latitude': None,  # Geo coordinates latitude
        'longitude': None,  # Geo coordinates longitude
        'practice_area_percentages': None,  # Practice area percentages from pie chart (JSON)
        'honors_awards': None,
        'associations': None,
        'work_experience': None,
        'endorsements_received': 0,
        'endorsements_given': 0,
        'legal_answers': 0,
        'biography': None,
        'professional_id': None,
        'specialty_id': None,
        'specialty_name': None,
        'claim_status': None,
        'additional_practice_areas': None,
        'total_reviews_extracted': 0,
        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'review_date_filter': None,  # Review date filter information (e.g., "Last 365 days (from 2024-12-27)" or "All reviews (no date filter)")
        # Nomenclature breakdown fields (Avvo format)
        'nomenclature_source': 'avvo',  # Source: avvo
        'nomenclature_id': None,  # Full ID: 94401-ca-haitham-ballout-336338
        'nomenclature_zip_code': None,  # 94401
        'nomenclature_state_code': None,  # ca
        'nomenclature_name': None,  # haitham-ballout
        'nomenclature_profile_id': None  # 336338
    }
    
    # Extract attorney name
    name_elem = soup.find('h1', class_='profile-name')
    if name_elem:
        data['attorney_full_name'] = name_elem.get_text(strip=True)
    
    # Extract profile URL from canonical link or current URL
    canonical = soup.find('link', rel='canonical')
    if canonical:
        data['profile_url'] = canonical.get('href')
    
    # Parse nomenclature from profile URL
    # Format: /attorneys/94401-ca-haitham-ballout-336338.html
    if data['profile_url']:
        match = re.search(r'/attorneys/([^/]+)\.html', data['profile_url'])
        if match:
            nomenclature_id = match.group(1)
            data['nomenclature_id'] = nomenclature_id
            
            # Parse the ID: 94401-ca-haitham-ballout-336338
            # Format: ZIP-STATE-NAME-PARTS-PROFILE_ID
            # Works with any number of name parts (1, 2, 3, 4+)
            # Examples:
            #   - 94401-ca-john-336338 (1 name part)
            #   - 94401-ca-haitham-ballout-336338 (2 name parts)
            #   - 94401-ca-mary-jane-smith-336338 (3 name parts)
            #   - 94401-ca-john-paul-smith-jones-336338 (4 name parts)
            parts = nomenclature_id.split('-')
            if len(parts) >= 4:
                # First part is zip code
                data['nomenclature_zip_code'] = parts[0]
                # Second part is state code
                data['nomenclature_state_code'] = parts[1].upper()  # Convert to uppercase (CA)
                # Last part is profile ID
                data['nomenclature_profile_id'] = parts[-1]
                # Middle parts (parts[2:-1]) are the name - handles 1, 2, 3, 4+ name parts
                name_parts = parts[2:-1]
                if name_parts:
                    # Join with space and capitalize each word
                    # This handles any number of name parts correctly
                    name = ' '.join(name_parts).replace('-', ' ').title()
                    data['nomenclature_name'] = name
    
    # Extract firm name
    firm_elem = soup.find('div', class_='location-detail')
    if firm_elem:
        firm_h4 = firm_elem.find('h4')
        if firm_h4:
            data['firm_name'] = firm_h4.get_text(strip=True)
    
    # Extract address
    location_elem = soup.find('p', id='masthead-location')
    if location_elem:
        address_text = location_elem.get_text(strip=True)
        data['company_address'] = address_text
        
        # Parse city, state, zip
        parts = [p.strip() for p in address_text.split(',')]
        if len(parts) >= 2:
            last_part = parts[-1].strip()
            state_zip = re.match(r'([A-Z]{2})\s*,?\s*(\d{5}(?:-\d{4})?)?', last_part)
            if state_zip:
                data['company_state'] = state_zip.group(1)
                if state_zip.group(2):
                    data['company_zip'] = state_zip.group(2)
            if len(parts) >= 2:
                data['company_city'] = parts[-2].strip()
    
    # Extract phone number
    phone_elem = soup.find('span', class_='overridable-lawyer-phone-copy')
    if not phone_elem:
        phone_elem = soup.find('a', href=re.compile(r'^tel:'))
    if phone_elem:
        if hasattr(phone_elem, 'get_text'):
            data['company_phone_number'] = phone_elem.get_text(strip=True)
        else:
            data['company_phone_number'] = phone_elem.get('href', '').replace('tel:', '').strip()
    
    # Extract fax number
    fax_elem = soup.find('span', class_='fax')
    if fax_elem:
        fax_parent = fax_elem.find_parent('a')
        if fax_parent:
            data['company_fax_number'] = fax_parent.get_text(strip=True)
    
    # Extract actual business website URL (not the Avvo redirect)
    # First try from href attribute (before onclick modifies it)
    if not data.get('company_website'):
        website_link = soup.find('a', class_='cta-website')
        if website_link:
            href = website_link.get('href', '')
            if href and not href.startswith('#') and not href.startswith('https://www.avvo.com'):
                data['company_website'] = href
        
        # Also try from location section website link
        if not data.get('company_website'):
            location_website_link = soup.find('a', class_='contact-website')
            if location_website_link:
                href = location_website_link.get('href', '')
                if href and not href.startswith('#') and not href.startswith('https://www.avvo.com'):
                    data['company_website'] = href
    
    # Extract review score
    review_score_elem = soup.find('span', class_='aggregated-ratings-count')
    if review_score_elem:
        try:
            data['overall_average_rating'] = float(review_score_elem.get_text(strip=True))
        except:
            pass
    
    # Extract total review count
    review_count_elem = soup.find('p', class_='aggregated-ratings-description')
    if review_count_elem:
        count_text = review_count_elem.get_text(strip=True)
        match = re.search(r'(\d+)\s+Client Reviews', count_text)
        if match:
            data['total_review_count'] = int(match.group(1))
    
    # Extract Avvo vs Lawyers.com review counts
    avvo_count = soup.find('p', class_='aggregrated-reviews-total')
    if avvo_count:
        match = re.search(r'\((\d+)\)', avvo_count.get_text())
        if match:
            data['avvo_reviews_count'] = int(match.group(1))
    
    ldc_count = soup.find('p', class_='aggregrated-reviews-total total-ldc')
    if ldc_count:
        match = re.search(r'\((\d+)\)', ldc_count.get_text())
        if match:
            data['lawyers_com_reviews_count'] = int(match.group(1))
    
    # Extract Avvo rating
    avvo_rating_text = soup.find('span', class_='avvo-rating-count')
    if avvo_rating_text:
        rating_text = avvo_rating_text.get_text(strip=True)
        match = re.search(r'Rating:\s*([\d.]+)', rating_text)
        if match:
            data['avvo_rating'] = float(match.group(1))
    
    # Extract rating description
    rating_desc = soup.find('span', class_='attorney-rating-level')
    if rating_desc:
        data['avvo_rating_description'] = rating_desc.get_text(strip=True)
    
    # Extract years licensed
    years_elem = soup.find('p', string=re.compile(r'Licensed for \d+ years'))
    if years_elem:
        years_text = years_elem.get_text(strip=True)
        data['years_licensed_text'] = years_text  # Full text: "Licensed for 35 years"
        match = re.search(r'Licensed for (\d+) years', years_text)
        if match:
            data['years_licensed'] = int(match.group(1))
            current_year = datetime.now().year
            data['year_licensed'] = current_year - int(match.group(1))
    
    # Extract practice areas - multiple methods with comprehensive fallbacks
    practice_areas = []
    
    # Method 1: Try to get from practice-area-list span (most complete)
    practice_area_list = soup.find('span', class_='practice-area-list')
    if practice_area_list:
        pa_text = practice_area_list.get_text(strip=True)
        # Split by comma and clean
        pa_list = [pa.strip() for pa in pa_text.split(',') if pa.strip()]
        practice_areas.extend(pa_list)
    
    # Method 2: From profile header
    if not practice_areas:
        pa_elems = soup.find_all('span', class_='profile-practice-area')
        for elem in pa_elems:
            pa_name = elem.get_text(strip=True)
            if pa_name and pa_name not in practice_areas:
                practice_areas.append(pa_name)
    
    # Method 3: From practice area section (practice-area-title links) - ALWAYS run
    pa_links = soup.find_all('a', class_='practice-area-title')
    for link in pa_links:
        # Get text from strong tags inside the link (more reliable)
        strong_tags = link.find_all('strong')
        if strong_tags:
            # First strong tag is usually the practice area name
            pa_name = strong_tags[0].get_text(strip=True)
            # Skip if it's a percentage (contains %)
            if pa_name and '%' not in pa_name and pa_name not in practice_areas:
                practice_areas.append(pa_name)
        else:
            # Fallback to link text
            pa_name = link.get_text(strip=True)
            if pa_name and pa_name not in practice_areas:
                practice_areas.append(pa_name)
    
    # Method 4: From practice-area-title strong tags directly
    pa_titles = soup.find_all('strong', class_='practice-area-title')
    for title in pa_titles:
        pa_name = title.get_text(strip=True)
        # Skip if it's a percentage or number
        if pa_name and '%' not in pa_name and not pa_name.isdigit() and pa_name not in practice_areas:
            practice_areas.append(pa_name)
    
    # Method 5: From practice-area-detail divs (pie chart section) - ALWAYS run to get all practice areas
    pa_detail_divs = soup.find_all('div', class_='practice-area-detail')
    for pa_div in pa_detail_divs:
        # Look for practice area name in practice-area-title
        pa_title = pa_div.find('div', class_='practice-area-title')
        if not pa_title:
            # Also check for practice-area-title as a link
            pa_title = pa_div.find('a', class_='practice-area-title')
        
        if pa_title:
            strong_tags = pa_title.find_all('strong')
            if strong_tags:
                # First strong tag is the practice area name
                pa_name = strong_tags[0].get_text(strip=True)
                # Skip percentages and numbers
                if pa_name and '%' not in pa_name and not pa_name.isdigit() and pa_name not in practice_areas:
                    practice_areas.append(pa_name)
                
                # Also check for additional practice areas in expanded elements
                # Look for expandedElement or similar divs that contain additional practice areas
                expanded_div = pa_div.find('div', class_=re.compile(r'expanded|expand', re.IGNORECASE))
                if expanded_div:
                    # Look for paragraphs that might contain additional practice areas
                    for p in expanded_div.find_all('p'):
                        p_text = p.get_text(strip=True)
                        # Check if it contains comma-separated practice areas
                        if ',' in p_text and len(p_text) > 5:
                            # Split by comma and add each as a practice area
                            additional_pas = [pa.strip() for pa in p_text.split(',') if pa.strip()]
                            for add_pa in additional_pas:
                                # Clean up the practice area name
                                add_pa_clean = add_pa.strip()
                                # Skip if it's too short or contains common non-practice-area words
                                if (add_pa_clean and len(add_pa_clean) > 2 and 
                                    add_pa_clean not in practice_areas and
                                    not any(word in add_pa_clean.lower() for word in ['years', 'cases', 'case', 'read more', 'see more'])):
                                    practice_areas.append(add_pa_clean)
    
    # Method 6: From practice-area-title links (alternative structure)
    if not practice_areas:
        pa_title_links = soup.find_all('a', href=re.compile(r'/.*-lawyer/'))
        for link in pa_title_links:
            strong = link.find('strong')
            if strong:
                pa_name = strong.get_text(strip=True)
                if pa_name and '%' not in pa_name and not pa_name.isdigit() and pa_name not in practice_areas:
                    practice_areas.append(pa_name)
    
    # Method 7: From "Practice Areas:" text pattern
    if not practice_areas:
        practice_areas_section = soup.find('h3', string=re.compile(r'Practice Areas', re.IGNORECASE))
        if practice_areas_section:
            # Look for practice area links or text in the following siblings
            parent = practice_areas_section.find_parent()
            if parent:
                # Find all links that might be practice areas
                pa_links = parent.find_all('a', href=re.compile(r'lawyer'))
                for link in pa_links:
                    pa_name = link.get_text(strip=True)
                    if pa_name and len(pa_name) > 2 and pa_name not in practice_areas:
                        # Filter out common non-practice-area text
                        if not any(word in pa_name.lower() for word in ['more', 'see', 'view', 'all', 'page']):
                            practice_areas.append(pa_name)
    
    # Method 8: Extract from JSON payload if available
    if not practice_areas:
        payload_div = soup.find('div', {'id': 'payload'})
        if payload_div and payload_div.get('data-payload'):
            try:
                payload_json = json.loads(payload_div['data-payload'])
                # Check for practice areas in various JSON fields
                if 'specialtyName' in payload_json:
                    specialty = payload_json.get('specialtyName')
                    if specialty and specialty not in practice_areas:
                        practice_areas.append(specialty)
            except:
                pass
    
    # Clean and deduplicate practice areas
    cleaned_practice_areas = []
    for pa in practice_areas:
        pa_clean = pa.strip()
        # Skip if empty, is a number, contains %, or is too short
        if pa_clean and not pa_clean.isdigit() and '%' not in pa_clean and len(pa_clean) > 2:
            # Remove common suffixes/prefixes
            pa_clean = re.sub(r'^\d+\s*%?\s*', '', pa_clean)  # Remove leading numbers/percentages
            pa_clean = re.sub(r'\s*%$', '', pa_clean)  # Remove trailing %
            if pa_clean and pa_clean not in cleaned_practice_areas:
                cleaned_practice_areas.append(pa_clean)
    
    if cleaned_practice_areas:
        data['practice_areas'] = ', '.join(cleaned_practice_areas)
        data['primary_practice_area'] = cleaned_practice_areas[0]
    
    # Extract "Lawyer at [Location]" from profile header
    # Format: "[Practice Area] Lawyer at [City, State]"
    # Find the grid-with-icon div that contains icon-practice-area
    practice_area_icons = soup.find_all('i', class_='icon-practice-area')
    for icon in practice_area_icons:
        grid_div = icon.find_parent('div', class_='grid-with-icon')
        if grid_div:
            # Find practice area span
            pa_span = grid_div.find('span', class_='profile-practice-area')
            # Find location span
            location_span = grid_div.find('span', class_='profile-location')
            
            if pa_span and location_span:
                pa_name = pa_span.get_text(strip=True)
                location_text = location_span.get_text(strip=True)
                # Combine: "Immigration Lawyer at San Mateo, CA"
                if location_text.startswith('at '):
                    location_text = location_text[3:]  # Remove "at " prefix
                data['lawyer_at_location'] = f"{pa_name} Lawyer at {location_text}"
                break
    
    # Extract languages
    languages = []
    lang_section = soup.find('div', class_='languages-list')
    if lang_section:
        lang_elems = lang_section.find_all('p')
        for elem in lang_elems:
            lang = elem.get_text(strip=True)
            if lang:
                languages.append(lang)
    
    if languages:
        data['languages_spoken'] = ', '.join(languages)
    
    # Extract PRO status
    pro_elem = soup.find('div', class_='pro')
    if pro_elem:
        data['is_pro'] = True
    
    # Extract free consultation
    consult_elem = soup.find('p', string=re.compile(r'Free Consultation'))
    if consult_elem:
        data['free_consultation'] = True
    
    # Extract virtual consultation availability
    # Look for "Virtual Consultation Available" text in the masthead area
    virtual_consult_elem = soup.find('p', string=re.compile(r'Virtual Consultation Available', re.IGNORECASE))
    if virtual_consult_elem:
        data['virtual_consultation_available'] = True
    else:
        # Also check for icon-video which indicates virtual consultation
        video_icon = soup.find('i', class_='icon-video')
        if video_icon:
            # Check if there's a "Virtual Consultation" text nearby
            parent_div = video_icon.find_parent('div', class_='flex-row-with-border-radius')
            if parent_div:
                virtual_text = parent_div.find('p', string=re.compile(r'Virtual', re.IGNORECASE))
                if virtual_text:
                    data['virtual_consultation_available'] = True
    
    # Extract fees
    fee_section = soup.find('section', class_='fees-section')
    if fee_section:
        # Look for contingency fee
        contingency = fee_section.find(string=re.compile(r'Contingency'))
        if contingency:
            match = re.search(r'(\d+)%', contingency)
            if match:
                data['contingency_fee'] = f"{match.group(1)}%"
        
        # Look for hourly rate
        hourly = fee_section.find(string=re.compile(r'\$\d+'))
        if hourly:
            match = re.search(r'\$(\d+)', hourly)
            if match:
                data['hourly_rate'] = f"${match.group(1)}"
    
    # Extract endorsements
    endorsement_received = soup.find('label', class_='endorsement-received-button')
    if endorsement_received:
        count_span = endorsement_received.find('span')
        if count_span:
            try:
                data['endorsements_received'] = int(count_span.get_text(strip=True))
            except:
                pass
    
    endorsement_given = soup.find('label', class_='endorsement-given-button')
    if endorsement_given:
        count_span = endorsement_given.find('span')
        if count_span:
            try:
                data['endorsements_given'] = int(count_span.get_text(strip=True))
            except:
                pass
    
    # Extract legal answers count
    legal_answers_section = soup.find('section', class_='legal-answers-count')
    if legal_answers_section:
        count_elem = legal_answers_section.find('strong')
        if count_elem:
            try:
                data['legal_answers'] = int(count_elem.get_text(strip=True))
            except:
                pass
    
    # Extract education
    education_list = []
    education_section = soup.find('section', class_='education-container')
    if education_section:
        exp_items = education_section.find_all('div', class_='experience')
        for item in exp_items:
            year_elem = item.find('p')
            school_elem = item.find('strong')
            degree_elems = item.find_all('p')
            
            if school_elem:
                year = year_elem.get_text(strip=True) if year_elem else ''
                school = school_elem.get_text(strip=True)
                degree = degree_elems[1].get_text(strip=True) if len(degree_elems) > 1 else ''
                education_list.append(f"{school} ({degree}) - {year}")
    
    if education_list:
        data['education'] = ' | '.join(education_list)
    
    # Extract bar admissions
    licenses = []
    license_section = soup.find('section', class_='license-container')
    if license_section:
        license_items = license_section.find_all('div', class_='license')
        for item in license_items:
            title = item.find('h4', class_='license-title')
            if title:
                licenses.append(title.get_text(strip=True))
    
    if licenses:
        data['bar_admissions'] = ' | '.join(licenses)
    
    # Extract honors/awards
    honors = []
    honors_section = soup.find('section', class_='honors-container')
    if honors_section:
        honor_items = honors_section.find_all('div', class_='experience')
        for item in honor_items:
            honor_text = item.get_text(strip=True)
            if honor_text:
                honors.append(honor_text)
    
    if honors:
        data['honors_awards'] = ' | '.join(honors)
    
    # Extract associations
    associations = []
    assoc_section = soup.find('section', class_='associations-container')
    if assoc_section:
        assoc_items = assoc_section.find_all('div', class_='experience')
        for item in assoc_items:
            assoc_name = item.find('strong')
            if assoc_name:
                associations.append(assoc_name.get_text(strip=True))
    
    if associations:
        data['associations'] = ' | '.join(associations)
    
    # Extract work experience
    work_exp = []
    work_section = soup.find('section', class_='work-experience-container')
    if work_section:
        work_items = work_section.find_all('div', class_='experience')
        for item in work_items:
            work_text = item.get_text(strip=True)
            if work_text:
                work_exp.append(work_text)
    
    if work_exp:
        data['work_experience'] = ' | '.join(work_exp)
    
    # Extract biography/About section
    about_section = soup.find('section', class_='about-container')
    if about_section:
        about_text = about_section.get_text(strip=True)
        # Clean up the text
        about_text = re.sub(r'\s+', ' ', about_text)
        data['biography'] = about_text
    
    # Extract JSON payload data (contains structured data)
    payload_div = soup.find('div', {'id': 'payload'})
    if payload_div and payload_div.get('data-payload'):
        try:
            payload_json = json.loads(payload_div['data-payload'])
            data['professional_id'] = payload_json.get('professionalId')
            data['specialty_id'] = payload_json.get('specialty_id')
            data['specialty_name'] = payload_json.get('specialtyName')
            data['claim_status'] = payload_json.get('claimStatus')
            
            # Override ratings from JSON if available (more accurate)
            if 'reviewScore' in payload_json:
                data['overall_average_rating'] = payload_json.get('reviewScore')
            if 'reviews' in payload_json:
                data['total_review_count'] = payload_json.get('reviews', 0)
            if 'rating' in payload_json:
                data['avvo_rating'] = payload_json.get('rating')
        except:
            pass
    
    # Extract additional practice areas links
    additional_pa_section = soup.find('aside', class_='additional-practice-areas-container')
    if additional_pa_section:
        pa_links = additional_pa_section.find_all('a')
        additional_pas = [link.get_text(strip=True) for link in pa_links if link.get_text(strip=True)]
        if additional_pas:
            data['additional_practice_areas'] = ' | '.join(additional_pas)
    
    # Extract JSON-LD structured data (contains profile photo, geo, payment methods, etc.)
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        try:
            json_data = json.loads(script.string)
            if json_data.get('@type') == 'LocalBusiness':
                # Extract profile photo URL
                if 'image' in json_data:
                    data['profile_photo_url'] = json_data['image']
                
                # Extract geo coordinates
                if 'geo' in json_data and json_data['geo'].get('@type') == 'GeoCoordinates':
                    data['latitude'] = json_data['geo'].get('latitude')
                    data['longitude'] = json_data['geo'].get('longitude')
                
                # Extract payment methods
                if 'paymentAccepted' in json_data:
                    data['payment_methods'] = json_data['paymentAccepted']
                
                # Extract currencies accepted
                if 'currenciesAccepted' in json_data:
                    data['currencies_accepted'] = json_data['currenciesAccepted']
                
                # Extract review count from aggregateRating
                if 'aggregateRating' in json_data:
                    rating_data = json_data['aggregateRating']
                    if 'reviewCount' in rating_data:
                        data['total_review_count'] = rating_data['reviewCount']
                    if 'ratingValue' in rating_data:
                        data['overall_average_rating'] = rating_data['ratingValue']
                
                # Extract makesOffer (retainer info)
                if 'makesOffer' in json_data:
                    data['retainer_info'] = json_data['makesOffer']
                
                # Extract actual business website URL from sameAs
                if 'sameAs' in json_data:
                    data['company_website'] = json_data['sameAs']
                
                break  # Only need the first LocalBusiness entry
        except:
            pass
    
    # Extract practice area percentages from pie chart
    practice_area_details = []
    practice_area_section = soup.find('div', class_='practice-area-contents')
    if practice_area_section:
        pa_detail_divs = practice_area_section.find_all('div', class_='practice-area-detail')
        for pa_div in pa_detail_divs:
            # Try both <div> and <a> tags with class 'practice-area-title'
            pa_title = pa_div.find('div', class_='practice-area-title')
            if not pa_title:
                # Fallback: check for <a> tag with class 'practice-area-title'
                pa_title = pa_div.find('a', class_='practice-area-title')
            
            if pa_title:
                strong_tags = pa_title.find_all('strong')
                if len(strong_tags) >= 2:
                    pa_name = strong_tags[0].get_text(strip=True)
                    pa_percentage = strong_tags[1].get_text(strip=True)
                    # Only add if both name and percentage are valid
                    if pa_name and pa_percentage and '%' in pa_percentage:
                        practice_area_details.append(f"{pa_name}: {pa_percentage}")
    
    if practice_area_details:
        # Format as readable string: "Immigration: 90%, General Practice: 10%"
        data['practice_area_percentages'] = ', '.join(practice_area_details)
    
    # Extract cost details and payment methods from Fees section
    fees_section = soup.find('section', class_='fees-and-rates-container')
    if fees_section:
        # Extract retainer info
        retainer_elem = fees_section.find('strong', string=re.compile(r'Retainer', re.IGNORECASE))
        if retainer_elem:
            retainer_parent = retainer_elem.find_parent('div')
            if retainer_parent:
                retainer_p = retainer_parent.find('p')
                if retainer_p:
                    retainer_text = retainer_p.get_text(strip=True)
                    if not data.get('retainer_info'):
                        data['retainer_info'] = f"Retainer: {retainer_text}"
                    elif data.get('retainer_info') and '%' in data['retainer_info']:
                        # Clean up the JSON-LD version if it has % at the end
                        data['retainer_info'] = data['retainer_info'].rstrip('%')
        
        # Extract payment methods from list
        payment_methods_list = []
        payment_ul = fees_section.find('ul')
        if payment_ul:
            payment_items = payment_ul.find_all('li')
            for item in payment_items:
                method = item.get_text(strip=True)
                if method:
                    payment_methods_list.append(method)
        
        if payment_methods_list and not data.get('payment_methods'):
            data['payment_methods'] = ', '.join(payment_methods_list)
        
        # Extract cost details
        cost_elements = []
        cost_h4 = fees_section.find('h4', string=re.compile(r'Cost', re.IGNORECASE))
        if cost_h4:
            # Find the parent div that contains cost information
            cost_parent = cost_h4.find_parent('div', class_='frc-sub-section-body')
            if cost_parent:
                # Find all divs with flex column that contain cost info
                cost_divs = cost_parent.find_all('div', style=re.compile(r'flex-direction: column'))
                for cost_div in cost_divs:
                    strong = cost_div.find('strong')
                    p = cost_div.find('p')
                    if strong and p:
                        cost_type = strong.get_text(strip=True)
                        cost_value = p.get_text(strip=True)
                        cost_elements.append(f"{cost_type}: {cost_value}")
        
        if cost_elements:
            data['cost_details'] = ' | '.join(cost_elements)
    
    # Extract detailed license information
    license_section = soup.find('section', class_='license-container')
    if license_section:
        license_details = []
        license_items = license_section.find_all('div', class_='license')
        for item in license_items:
            license_parts = []
            
            # State
            state_elem = item.find('span', class_='state')
            state = None
            if state_elem:
                state = state_elem.get_text(strip=True)
            
            # Acquired date
            date_elem = item.find('span', class_='date')
            acquired = None
            if date_elem:
                acquired = date_elem.get_text(strip=True)
            
            # Status
            status_elem = item.find('span', class_='status-pill')
            status = None
            if status_elem:
                status = status_elem.get_text(strip=True)
            
            # Status description
            status_desc = item.find('p', class_='license-status')
            status_description = None
            if status_desc:
                status_description = status_desc.get_text(strip=True)
            
            # Build readable format: "State (Acquired: Year, Status: Status, Description)"
            if state:
                license_info_parts = [state]
                details = []
                
                if acquired:
                    details.append(f"Acquired: {acquired}")
                if status:
                    details.append(f"Status: {status}")
                if status_description:
                    details.append(status_description)
                
                if details:
                    license_info_parts.append(f"({', '.join(details)})")
                
                license_details.append(' '.join(license_info_parts))
        
        if license_details:
            # Format multiple licenses separated by " | "
            data['license_details'] = ' | '.join(license_details)
    
    # Extract send message link
    message_link = soup.find('a', class_='v-cta-message')
    if message_link and message_link.get('href'):
        data['send_message_link'] = message_link['href']
    else:
        # Try alternative selectors
        message_link = soup.find('a', {'data-pp': 'msg_initiated'})
        if message_link and message_link.get('href'):
            data['send_message_link'] = message_link['href']
    
    # Extract Google Maps directions link
    directions_link = soup.find('a', string=re.compile(r'Get Directions', re.IGNORECASE))
    if directions_link and directions_link.get('href'):
        data['google_map_directions_link'] = directions_link['href']
    else:
        # Try alternative selector
        directions_link = soup.find('a', {'aria_label': 'Get Directions'})
        if directions_link and directions_link.get('href'):
            data['google_map_directions_link'] = directions_link['href']
    
    # Extract profile photo URL from img tag if not found in JSON-LD
    if not data.get('profile_photo_url'):
        profile_img = soup.find('img', alt=re.compile(r'headshot', re.IGNORECASE))
        if profile_img and profile_img.get('src'):
            data['profile_photo_url'] = profile_img['src']
        else:
            # Try finding img with headshot in src
            profile_img = soup.find('img', src=re.compile(r'head_shot', re.IGNORECASE))
            if profile_img and profile_img.get('src'):
                data['profile_photo_url'] = profile_img['src']
    
    # Extract individual reviews
    reviews = []
    review_containers = soup.find_all('div', class_='client-review')
    for container in review_containers:
        review_data = {
            'reviewer_name': None,
            'review_date': None,
            'review_rating': 0,
            'review_title': None,
            'review_text': None,
            'review_type': None,  # e.g., "Consulted Attorney"
            'review_tooltip': None,  # Tooltip explanation if available
            # Attorney response fields
            'attorney_response_name': None,  # Attorney name who replied
            'attorney_response_date': None,  # Date attorney replied
            'attorney_response_text': None  # Attorney's reply text
        }
        
        # Extract rating (count stars)
        star_icons = container.find_all('i', class_='icon-star-yellow')
        review_data['review_rating'] = len(star_icons)
        
        # Extract reviewer name and date
        header = container.find('div', class_='client-review-header')
        if header:
            # Extract tooltip text first (if exists) - this is helpful information
            tooltip = header.find('span', class_='tooltiptext')
            if tooltip:
                review_data['review_tooltip'] = tooltip.get_text(strip=True)
            
            # Get the main paragraph
            first_para = header.find('p')
            if first_para:
                # Extract review type from span (if exists) - clean, no tooltip text
                review_type_span = first_para.find('span')
                if review_type_span and not review_type_span.find_parent('div', class_='tooltip'):
                    type_text = review_type_span.get_text(strip=True)
                    # Clean up pipes and extract just the type (no tooltip text)
                    type_text = type_text.strip('|').strip()
                    if type_text and 'This review is from' not in type_text:
                        review_data['review_type'] = type_text
                
                # Get all text from paragraph
                para_text = first_para.get_text(separator=' ', strip=True)
                # Remove review type from text if it was extracted
                if review_data['review_type']:
                    para_text = para_text.replace(f"| {review_data['review_type']}", "").strip()
                
                # Extract "Posted by NAME | DATE"
                match = re.search(r'Posted by (.+?)\s*\|\s*(.+?)(?:\s*\|)?$', para_text)
                if match:
                    review_data['reviewer_name'] = match.group(1).strip()
                    date_str = match.group(2).strip()
                    
                    # Parse date
                    try:
                        for fmt in ['%B %d, %Y', '%b %d, %Y', '%m/%d/%Y', '%B %d,%Y']:
                            try:
                                review_date = datetime.strptime(date_str, fmt)
                                review_data['review_date'] = review_date.strftime('%Y-%m-%d')
                                break
                            except:
                                continue
                    except:
                        pass
        
        # Extract review title
        title_elem = container.find('h4')
        if title_elem:
            review_data['review_title'] = title_elem.get_text(strip=True)
        
        # Extract review text
        content = container.find('div', class_='client-review-content')
        if content:
            text_parts = []
            for p in content.find_all('p'):
                for span in p.find_all('span'):
                    text = span.get_text(strip=True)
                    if text and text not in ['...', '…', 'See Full Review']:
                        text_parts.append(text)
            review_data['review_text'] = ' '.join(text_parts).strip()
        
        # Extract attorney response (if exists)
        response_container = container.find('div', class_='attorney-review-response-container')
        if response_container:
            # Extract attorney name
            attorney_name_h4 = response_container.find('h4')
            if attorney_name_h4:
                review_data['attorney_response_name'] = attorney_name_h4.get_text(strip=True)
            
            # Extract reply date
            reply_date_span = response_container.find('span')
            if reply_date_span:
                reply_date_text = reply_date_span.get_text(strip=True)
                # Parse "Replied last August 3, 2025" or "Replied last Aug 3, 2025"
                date_match = re.search(r'Replied last (.+)', reply_date_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1).strip()
                    # Parse date
                    try:
                        for fmt in ['%B %d, %Y', '%b %d, %Y', '%m/%d/%Y', '%B %d,%Y']:
                            try:
                                reply_date = datetime.strptime(date_str, fmt)
                                review_data['attorney_response_date'] = reply_date.strftime('%Y-%m-%d')
                                break
                            except:
                                continue
                    except:
                        pass
            
            # Extract reply text
            reply_text_p = response_container.find('p')
            if reply_text_p:
                review_data['attorney_response_text'] = reply_text_p.get_text(strip=True)
        
        if review_data['review_text'] or review_data['review_title']:
            reviews.append(review_data)
    
    if reviews:
        data['total_reviews_extracted'] = len(reviews)
    
    # Set review date filter info if provided
    if review_date_filter:
        data['review_date_filter'] = review_date_filter
    
    # Return both data and reviews list
    return data, reviews


def save_to_csv(data, reviews, output_csv_path):
    """
    Save extracted data and reviews to CSV file
    
    Args:
        data: Dictionary with profile data
        reviews: List of review dictionaries
        output_csv_path: Path to output CSV file
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
    
    # Save to CSV - use minimal quoting (only when needed) like the working example
    df.to_csv(output_csv_path, index=False, encoding='utf-8', quoting=csv.QUOTE_MINIMAL)
    
    # Display review count
    if reviews:
        print(f"✅ Created {len(rows)} rows ({len(reviews)} reviews + profile data in each row)")
    else:
        print(f"✅ Created 1 row (profile data, no reviews)")
    
    print(f"✅ Successfully saved to CSV: {output_csv_path}")
    print(f"\n📊 Extracted Data Summary:")
    print(f"   - Attorney Name: {data['attorney_full_name']}")
    print(f"   - Firm: {data['firm_name']}")
    print(f"   - Location: {data['company_city']}, {data['company_state']}")
    print(f"   - Rating: {data['overall_average_rating']}/5.0 ({data['total_review_count']} reviews)")
    print(f"   - Avvo Rating: {data['avvo_rating']}/10.0")
    print(f"   - Practice Areas: {data['practice_areas']}")
    if data.get('biography'):
        bio_preview = data['biography'][:100] + "..." if len(data['biography']) > 100 else data['biography']
        print(f"   - Biography: {bio_preview}")
    print(f"\n📋 Total columns extracted: {len(df.columns)}")
    
    return True


def convert_html_to_csv(html_file_path, output_csv_path=None):
    """
    Convert HTML file to CSV
    
    Args:
        html_file_path: Path to input HTML file
        output_csv_path: Path to output CSV file (optional)
    """
    print(f"📄 Reading HTML file: {html_file_path}")
    
    data, reviews = extract_profile_data(html_file_path)
    
    if not data:
        print("❌ Failed to extract data from HTML")
        return False
    
    # Generate output filename from user ID if not provided
    if not output_csv_path:
        # Extract user ID from profile URL (e.g., 90069-ca-michelle-paul-1896813)
        profile_url = data.get('profile_url', '')
        if profile_url:
            # Extract the ID part from URL like: /attorneys/90069-ca-michelle-paul-1896813.html
            match = re.search(r'/attorneys/([^/]+)\.html', profile_url)
            if match:
                user_id = match.group(1)
                output_csv_path = f"{user_id}.csv"
            else:
                # Fallback to professional_id or default name
                user_id = data.get('professional_id', 'unknown')
                output_csv_path = f"{user_id}.csv"
        else:
            base_name = os.path.splitext(os.path.basename(html_file_path))[0]
            output_csv_path = f"{base_name}.csv"
    
    return save_to_csv(data, reviews, output_csv_path)


def find_html_files(directory='.'):
    """
    Find all HTML files in the specified directory
    
    Args:
        directory: Directory to search (default: current directory)
        
    Returns:
        List of HTML file paths
    """
    html_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.html') and os.path.isfile(os.path.join(directory, filename)):
            html_files.append(os.path.join(directory, filename))
    return sorted(html_files)


def main():
    """
    Main function - processes all HTML files in current directory or specific file
    """
    print("=" * 70)
    print("HTML TO CSV CONVERTER - Avvo Profile Parser")
    print("=" * 70)
    
    # Check if specific file path provided as argument
    if len(sys.argv) > 1:
        # Process specific file
        html_file = sys.argv[1]
        if not os.path.exists(html_file):
            print(f"❌ Error: File '{html_file}' not found!")
            return
        
        output_file = None
        if len(sys.argv) > 2:
            output_file = sys.argv[2]
        
        convert_html_to_csv(html_file, output_file)
    else:
        # Find and process all HTML files in current directory
        html_files = find_html_files('.')
        
        if not html_files:
            print("❌ No HTML files found in current directory!")
            print("   Place HTML files in the same folder as this script")
            return
        
        print(f"\n📁 Found {len(html_files)} HTML file(s) to process:\n")
        for i, html_file in enumerate(html_files, 1):
            print(f"   {i}. {os.path.basename(html_file)}")
        
        print(f"\n{'='*70}")
        print(f"Processing {len(html_files)} file(s)...")
        print(f"{'='*70}\n")
        
        successful = 0
        failed = 0
        
        for i, html_file in enumerate(html_files, 1):
            print(f"\n[{i}/{len(html_files)}] Processing: {os.path.basename(html_file)}")
            print("-" * 70)
            
            if convert_html_to_csv(html_file):
                successful += 1
            else:
                failed += 1
        
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Successfully processed: {successful} file(s)")
        if failed > 0:
            print(f"❌ Failed: {failed} file(s)")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

