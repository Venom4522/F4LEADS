"""
F4Leads Scraper v3 — INTENT-BASED lead discovery.
Finds leads actively LOOKING for CGI/VFX services (job posts, RFPs, directories).
NOT random web results.
"""
import re, time, random, logging
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from engine.scorer import score_lead
from engine.outreach import generate_outreach

logger = logging.getLogger(__name__)

# ─── INTENT-BASED QUERIES (Finding leads actively seeking CGI/VFX) ───
# These queries find: job posts, RFPs, quote requests, project announcements
INTENT_QUERIES = {
    'brand_cgi': [
        # Job posts / hiring
        'need 3D product visualization freelancer',
        'looking for CGI artist for product video',
        'hiring 3D animator for e-commerce',
        'product commercial production needed',
        'CGI studio needed for brand campaign',
        # RFPs / quotes
        '3D product render quote request',
        'product animation quote',
        ' CGI commercial budget quote',
        # Directories
        'product visualization studio directory',
        'top CGI companies for e-commerce',
    ],
    'ott_film': [
        'VFX artist required for series',
        'need VFX studio for film',
        'outsourcing VFX work streaming',
        'post production VFX contract',
        'looking for VFX supervisor',
        'CGI company for film VFX',
    ],
    'archviz': [
        'real-time walkthrough quote',
        'archviz studio needed',
        'Unreal Engine 3D walkthrough',
        'architectural rendering service',
        '3D visualization company quote',
    ],
    'gaming': [
        'need 3D artist for game',
        'game asset outsourcing',
        'Unity Unreal artist needed',
        'indie game studio 3D artist',
    ],
    'product_viz': [
        '3D product rendering service',
        'product CGI studio',
        'ecommerce 3D renders needed',
        'product visualization quote',
        '360 product spin studio',
    ],
}

# Additional: Search by PLATFORMS where CGI/VFX work is posted
PLATFORM_QUERIES = {
    'upwork': [
        '3D visualization job post',
        'CGI artist job',
        'product animation upwork',
    ],
    'freelancer': [
        '3D rendering project',
        'CGI freelance project',
    ],
    'fiverr': [
        '3D product visualization gig',
        'CGI animation service',
    ],
}

# ─── COMPANY LISTS (Pre-verified D2C brands with budgets) ───
VERIFIED_DTC_BRANDS = [
    # From funding news - these brands HAVE BUDGETS
    {'name': 'ClayCo', 'niche': 'beauty', 'country': 'India'},
    {'name': 'AntiNorm', 'niche': 'beauty', 'country': 'India'},
    {'name': 'Unbound', 'niche': 'personal care', 'country': 'India'},
    {'name': 'Salty', 'niche': 'fashion', 'country': 'India'},
    {'name': 'Bluetyga', 'niche': 'apparel', 'country': 'India'},
    # Add more verified brands from research
]

# ─── BUSINESS DIRECTORIES (Companies that buy CGI) ───
DIRECTORIES = [
    'https://www.clutch.co/categories/video-production',
    'https://www.goodfirms.co/category/video-production',
    'https://www.theplacesto.be/',
]

EMAIL_BLACKLIST = {
    'example.com', 'sentry.io', 'wixpress.com', 'schema.org',
    'googleapis.com', 'w3.org', 'apple.com', 'google.com',
    'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
    'wordpress.org', 'wordpress.com', 'gravatar.com', 'cloudflare.com',
    'jsdelivr.net', 'gstatic.com', 'bootstrapcdn.com', 'jquery.com',
    'unpkg.com', 'cdnjs.com', 'maxcdn.com',
}

SKIP_DOMAINS = {
    'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
    'youtube.com', 'wikipedia.org', 'reddit.com', 'quora.com',
    'medium.com', 'glassdoor.com', 'indeed.com', 'naukri.com',
    'justdial.com', 'sulekha.com', 'crunchbase.com', 'zaubacorp.com',
    'tofler.in', 'ambitionbox.com', 'google.com', 'yelp.com',
    'pinterest.com', 'tiktok.com', 'amazon.com', 'flipkart.com',
    'ebay.com', 'etsy.com', 'alibaba.com', 'aliexpress.com',
    'tripadvisor.com', 'trustpilot.com', 'bbb.org', 'yellowpages.com',
    'bing.com', 'yahoo.com', 'duckduckgo.com',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# High-value countries (where clients have budgets)
HIGH_VALUE_COUNTRIES = ['United States', 'United Kingdom', 'UAE', 'Australia', 'Canada', 'Germany', 'France', 'Netherlands', 'Sweden', 'Singapore']


class LeadScraper:
    """INTENT-BASED lead scraping: find leads actively seeking CGI/VFX services."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.found_domains = set()

    def generate_leads(self, niche='brand_cgi', max_queries=6, results_per_query=12, progress_callback=None):
        """Main entry: Intent-based search → Verified directories → Enrich → Score."""
        all_leads = []

        # Phase 1: Intent searches (job posts, RFPs, quotes)
        if progress_callback:
            progress_callback("Finding leads actively looking for CGI/VFX...", 5)
        intent_leads = self._intent_search(niche, max_queries, results_per_query, progress_callback)
        all_leads.extend(intent_leads)

        # Phase 2: Verified D2C brands (from funding news)
        if progress_callback:
            progress_callback("Adding verified D2C brands...", 30)
        verified_leads = self._verified_brands(niche)
        all_leads.extend(verified_leads)

        # Phase 3: Business directories
        if progress_callback:
            progress_callback("Searching business directories...", 50)
        directory_leads = self._directory_search(niche, progress_callback)
        all_leads.extend(directory_leads)

        logger.info(f"Raw leads collected: {len(all_leads)}")

        # Phase 4: Deep enrichment (get contact info)
        if progress_callback:
            progress_callback(f"Enriching {len(all_leads)} leads...", 60)
        enriched = self._enrich_batch(all_leads)

        # Phase 5: Quality filter
        if progress_callback:
            progress_callback("Applying quality filters...", 80)
        quality_leads = self._quality_filter(enriched)

        # Phase 6: Score
        if progress_callback:
            progress_callback("Scoring leads...", 90)
        for lead in quality_leads:
            lead['icp_score'] = score_lead(lead)
            lead['outreach_draft'] = generate_outreach(lead)

        quality_leads.sort(key=lambda x: x['icp_score'], reverse=True)

        if progress_callback:
            progress_callback(f"Done! {len(quality_leads)} quality leads.", 100)
        
        return quality_leads

    # ─── INTENT SEARCH ────────────────────────────────────────────────────────
    def _intent_search(self, niche, max_queries, results_per_query, progress_callback):
        """Search for leads ACTIVELY seeking CGI services."""
        queries = INTENT_QUERIES.get(niche, INTENT_QUERIES['brand_cgi'])
        selected = random.sample(queries, min(max_queries, len(queries)))
        leads = []

        for i, query in enumerate(selected):
            if progress_callback:
                progress_callback(f"Searching: {query[:40]}...", 10 + (i / len(selected)) * 20)
            try:
                # Use DDGS to find intent-based results
                results = DDGS().text(query, max_results=results_per_query, region='wt-wt')
                logger.info(f"Intent '{query}' → {len(results or [])} results")
                for r in (results or []):
                    lead = self._process_result(r, niche, query)
                    if lead and lead['domain'] not in self.found_domains:
                        self.found_domains.add(lead['domain'])
                        lead['source'] = f'Intent: "{query}"'
                        leads.append(lead)
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                logger.error(f"Intent search error '{query}': {e}")
                time.sleep(2)
        return leads

    # ─── VERIFIED BRANDS ──────────────────────────────────────────────────────
    def _verified_brands(self, niche):
        """Add verified D2C brands WITH FUNDING (they have budgets)."""
        leads = []
        for brand in VERIFIED_DTC_BRANDS:
            domain = f"{brand['name'].lower()}.com"
            if domain in self.found_domains:
                continue
            self.found_domains.add(domain)
            leads.append({
                'company_name': brand['name'],
                'website': f'https://{domain}',
                'domain': domain,
                'contact_name': '',
                'contact_role': '',
                'contact_email': '',
                'phone_number': '',
                'linkedin_url': '',
                'instagram_url': '',
                'niche': niche,
                'location': brand['country'],
                'description': f"Funded {brand['niche']} brand - potential client",
                'signals': ['Verified D2C brand with funding'],
                'icp_score': 0,
                'stage': 'research',
                'outreach_draft': '',
                'notes': '',
                'source': 'Verified list',
            })
        return leads

    # ─── DIRECTORY SEARCH ────────────────────────────────────────────────
    def _directory_search(self, niche, progress_callback):
        """Search business directories for CGI/VFX providers (their clients)."""
        leads = []
        for i, dir_url in enumerate(DIRECTORIES[:3]):
            if progress_callback:
                progress_callback(f"Searching directory: {dir_url.split('/')[-2]}...", 40)
            try:
                resp = self.session.get(dir_url, timeout=10)
                if resp.ok:
                    soup = BeautifulSoup(resp.text, 'lxml')
                    # Extract company listings
                    for item in soup.find_all('a', href=True)[:15]:
                        href = item.get('href', '')
                        title = item.get_text(strip=True)
                        if 'http' in href and '.' in title and len(title) > 2:
                            try:
                                parsed = urlparse(href)
                                domain = parsed.netloc.replace('www.', '')
                                if domain not in self.found_domains and 'clutch' not in domain:
                                    self.found_domains.add(domain)
                                    leads.append({
                                        'company_name': title[:50],
                                        'website': href,
                                        'domain': domain,
                                        'contact_name': '',
                                        'contact_role': '',
                                        'contact_email': '',
                                        'phone_number': '',
                                        'linkedin_url': '',
                                        'instagram_url': '',
                                        'niche': niche,
                                        'location': '',
                                        'description': f"Business directory listing: {title[:100]}",
                                        'signals': ['Directory listing'],
                                        'icp_score': 0,
                                        'stage': 'research',
                                        'outreach_draft': '',
                                        'notes': '',
                                        'source': f'Directory: {dir_url}',
                                    })
                            except:
                                pass
            except Exception as e:
                logger.error(f"Directory error: {e}")
        return leads

    # ─── PROCESS RESULTS ───────────────────────────────────────────────��─────
    def _process_result(self, result, niche, query):
        """Process a search result into a lead."""
        url = result.get('href', '')
        if not url:
            return None
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').lower()
        
        # Skip directories and generic sites
        if any(s in domain for s in SKIP_DOMAINS):
            return None
        
        company_name = self._extract_company_name(result.get('title', ''), domain)
        description = (result.get('body', '') or '')[:300]
        
        # Only keep if there's useful info
        if not company_name or len(company_name) < 2:
            return None
            
        return {
            'company_name': company_name,
            'website': f"{parsed.scheme}://{parsed.netloc}",
            'domain': domain,
            'contact_name': '',
            'contact_role': '',
            'contact_email': '',
            'phone_number': '',
            'linkedin_url': '',
            'instagram_url': '',
            'niche': niche,
            'location': '',
            'description': description,
            'signals': [f'Found via: {query}'],
            'icp_score': 0,
            'stage': 'research',
            'outreach_draft': '',
            'notes': '',
            'source': f'Web: "{query}"',
        }

    # ─── ENRICHMENT ─────────────────────────────────────────────────────
    def _enrich_batch(self, leads, max_workers=4):
        """Enrich leads with contact info."""
        enriched = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._enrich_lead, l): l for l in leads}
            for future in as_completed(futures):
                try:
                    enriched.append(future.result())
                except Exception as e:
                    logger.error(f"Enrichment error: {e}")
                    enriched.append(futures[future])
        return enriched

    def _enrich_lead(self, lead):
        """Enrich a single lead with contact info from website."""
        website = lead.get('website', '')
        if not website:
            return lead
        try:
            resp = self.session.get(website, timeout=8, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # Extract emails
            emails = self._extract_emails(resp.text, lead['domain'])
            if emails:
                lead['contact_email'] = emails[0]
            
            # Extract phones
            phones = self._extract_phones(soup, resp.text)
            if phones and not lead['phone_number']:
                lead['phone_number'] = phones[0]
            
            # Extract social links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                if 'linkedin.com/company' in href and not lead['linkedin_url']:
                    lead['linkedin_url'] = href
                elif 'instagram.com/' in href and not lead['instagram_url']:
                    if 'instagram.com/p/' not in href:
                        lead['instagram_url'] = href
            
            # Try contact page
            self._scrape_contact_page(website, lead)
            
        except requests.RequestException as e:
            logger.debug(f"Could not fetch {website}: {e}")
        return lead

    def _scrape_contact_page(self, base_url, lead):
        """Scrape contact page for email/phone."""
        contact_paths = ['contact', 'contact-us', 'reach-us', 'connect', 'get-in-touch']
        for path in contact_paths:
            try:
                url = urljoin(base_url, f'/{path}/')
                r = self.session.get(url, timeout=5)
                if r.ok:
                    emails = self._extract_emails(r.text, lead['domain'])
                    phones = self._extract_phones(BeautifulSoup(r.text, 'lxml'), r.text)
                    if emails and not lead['contact_email']:
                        lead['contact_email'] = emails[0]
                    if phones and not lead['phone_number']:
                        lead['phone_number'] = phones[0]
                    if lead['contact_email'] or lead['phone_number']:
                        return
            except:
                pass

    def _extract_emails(self, html_text, domain):
        """Extract valid emails."""
        pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
        raw = re.findall(pattern, html_text)
        valid = []
        for e in raw:
            e = e.lower().strip('.')
            ed = e.split('@')[1]
            if any(bl in ed for bl in EMAIL_BLACKLIST):
                continue
            if ed.endswith(('.png', '.jpg', '.gif', '.svg', '.css', '.js')):
                continue
            valid.append(e)
        # Prefer domain emails
        same = [e for e in valid if domain in e]
        other = [e for e in valid if domain not in e]
        return (same + other)[:3]

    def _extract_phones(self, soup, html_text):
        """Extract phone numbers."""
        phones = []
        # tel: links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('tel:'):
                phone = href.replace('tel:', '').strip()
                if len(re.sub(r'\D', '', phone)) >= 7:
                    phones.append(phone)
        # Regex
        text = soup.get_text(separator=' ', strip=True)
        phone_pattern = r'(?:\+\d{1,3}[\s.\-]?)?\(?\d{2,4}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}'
        for match in re.findall(phone_pattern, text):
            digits = re.sub(r'\D', '', match)
            if 7 <= len(digits) <= 15:
                phones.append(match.strip())
        return list(set(phones))[:3]

    # ─── QUALITY FILTER ────────────────────────────────────────────
    def _quality_filter(self, leads):
        """Filter for leads with contact info OR verified."""
        quality = []
        for lead in leads:
            has_email = bool(lead.get('contact_email'))
            has_phone = bool(lead.get('phone_number'))
            has_website = bool(lead.get('website'))
            has_description = len(lead.get('description', '')) > 15
            
            # Keep if: contact info OR website+description OR verified source
            is_verified = lead.get('source') == 'Verified list'
            if has_email or has_phone or (has_website and has_description) or is_verified:
                quality.append(lead)
        logger.info(f"Quality filter: {len(leads)} → {len(quality)}")
        return quality

    def _extract_company_name(self, title, domain):
        """Extract company name from title."""
        for sep in [' - ', ' | ', ' — ', ' :: ', ' – ']:
            if sep in title:
                title = title.split(sep)[0].strip()
                break
        if len(title) > 60 or not title:
            title = domain.split('.')[0].replace('-', ' ').replace('_', ' ').title()
        return title