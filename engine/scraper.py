"""
F4Leads Scraper v2 — International D2C lead discovery engine.
Multi-source: DuckDuckGo Web + DuckDuckGo Maps + Deep website crawling.
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

# ─── SEARCH QUERIES (INTERNATIONAL D2C FOCUS) ────────────────────────────────
WEB_QUERIES = {
    'brand_cgi': [
        'DTC brand product launch 2025 2026',
        'direct to consumer brand CMO marketing',
        'Shopify brand product commercial video',
        'ecommerce brand CGI product visualization',
        'beauty skincare brand product campaign',
        'consumer electronics brand product marketing',
        'fashion DTC brand founder CEO ecommerce',
        'food beverage brand product photography',
        'wellness lifestyle brand product launch',
        'sustainable brand ecommerce founder',
        'luxury premium brand product visualization',
        'D2C brand Series A funded startup',
        'UK DTC brand product launch ecommerce',
        'European DTC brand direct consumer',
        'Dubai UAE luxury brand ecommerce',
        'Australian DTC brand founder ecommerce',
        'Canadian direct consumer brand startup',
        'beauty brand new product campaign 2026',
        'home decor brand DTC ecommerce',
        'pet brand direct consumer products',
    ],
    'ott_film': [
        'film production company visual effects VFX',
        'OTT series production VFX partner',
        'streaming content production company',
        'post production studio outsourcing VFX',
        'commercial production company CGI',
        'animation studio feature film production',
        'independent film producer VFX needs',
        'TV series production visual effects',
        'Netflix Amazon production company VFX',
        'documentary production CGI effects',
    ],
    'archviz': [
        'architecture firm 3D visualization rendering',
        'real estate developer CGI walkthrough',
        'architectural visualization company',
        'interior design studio 3D rendering',
        'property developer CGI marketing',
        'real estate rendering walkthrough company',
        'luxury real estate visualization',
        'commercial property developer renders',
    ],
    'gaming': [
        'indie game studio 3D art',
        'game development company assets',
        'mobile game developer 3D artist',
        'game art outsourcing studio',
        'Unity Unreal game studio indie',
        'game design company 3D modeling',
        'VR AR game studio development',
        'metaverse game development company',
    ],
    'product_viz': [
        'product visualization 3D rendering company',
        'ecommerce product photography 3D CGI',
        'product animation company rendering',
        'Amazon product listing 3D renders',
        'packaging design 3D visualization',
        'industrial product visualization CGI',
        'product CGI commercial studio',
        'furniture product 3D rendering',
    ],
}

# Maps queries: category + cities for local business discovery
MAPS_QUERIES = {
    'brand_cgi': ['cosmetics company', 'skincare brand', 'fashion brand', 'DTC brand', 'ecommerce company', 'consumer brand'],
    'ott_film': ['film production company', 'VFX studio', 'post production studio', 'animation studio', 'video production company'],
    'archviz': ['architecture firm', 'real estate developer', 'interior design studio', 'architectural visualization'],
    'gaming': ['game development studio', 'game design company', 'indie game studio'],
    'product_viz': ['product photography studio', '3D rendering company', 'product design studio'],
}

MAPS_CITIES = [
    'New York', 'Los Angeles', 'San Francisco', 'Chicago', 'Austin', 'Miami',
    'London', 'Manchester', 'Berlin', 'Amsterdam', 'Paris', 'Stockholm',
    'Dubai', 'Abu Dhabi', 'Sydney', 'Melbourne', 'Toronto', 'Singapore',
]

MAPS_CITIES_INDIA = ['Mumbai', 'Delhi', 'Bangalore', 'Pune', 'Hyderabad', 'Chennai']

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

# Country detection keywords
COUNTRY_MAP = {
    'United States': ['usa', 'united states', 'u.s.', 'america'],
    'United Kingdom': ['uk', 'united kingdom', 'britain', 'england', 'scotland', 'wales'],
    'Germany': ['germany', 'deutschland'], 'France': ['france'],
    'Netherlands': ['netherlands', 'holland'], 'Sweden': ['sweden'],
    'UAE': ['uae', 'dubai', 'abu dhabi', 'united arab emirates'],
    'Australia': ['australia'], 'Canada': ['canada'],
    'Singapore': ['singapore'], 'India': ['india'],
}

INDIAN_CITIES = [
    'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'chennai',
    'kolkata', 'pune', 'noida', 'gurgaon', 'gurugram', 'ahmedabad',
    'jaipur', 'lucknow', 'chandigarh', 'kochi', 'indore', 'coimbatore',
    'new delhi', 'ncr', 'goa',
]

INTL_CITIES = [
    'new york', 'los angeles', 'san francisco', 'chicago', 'austin', 'miami',
    'london', 'manchester', 'berlin', 'amsterdam', 'paris', 'stockholm',
    'dubai', 'abu dhabi', 'sydney', 'melbourne', 'toronto', 'singapore',
    'seattle', 'boston', 'denver', 'atlanta', 'dallas', 'houston',
    'bristol', 'edinburgh', 'munich', 'hamburg', 'barcelona', 'madrid',
    'copenhagen', 'oslo', 'helsinki', 'lisbon', 'milan', 'rome',
    'riyadh', 'doha', 'kuwait', 'brisbane', 'perth', 'auckland',
    'vancouver', 'montreal', 'hong kong', 'tokyo', 'seoul',
]

DECISION_MAKER_TITLES = [
    'founder', 'co-founder', 'ceo', 'cto', 'cmo', 'coo', 'cfo',
    'director', 'head', 'vp', 'vice president', 'manager',
    'lead', 'chief', 'owner', 'partner', 'president',
    'marketing', 'creative', 'production', 'brand',
]


class LeadScraper:
    """Multi-source lead scraping engine for AtmonFX."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.found_domains = set()

    def generate_leads(self, niche='brand_cgi', max_queries=6, results_per_query=12, progress_callback=None):
        """Main entry: Web Search + Maps Search → Scrape → Enrich → Score → Outreach."""
        all_leads = []

        # Phase 1: Web search
        if progress_callback:
            progress_callback("Searching the web for prospects...", 5)
        web_leads = self._web_search(niche, max_queries, results_per_query, progress_callback)
        all_leads.extend(web_leads)

        # Phase 2: Maps search
        if progress_callback:
            progress_callback("Searching maps for businesses...", 30)
        maps_leads = self._maps_search(niche, progress_callback)
        all_leads.extend(maps_leads)

        logger.info(f"Raw leads collected: {len(all_leads)} (web: {len(web_leads)}, maps: {len(maps_leads)})")

        # Phase 3: Deep enrichment
        if progress_callback:
            progress_callback(f"Enriching {len(all_leads)} leads from websites...", 50)
        enriched = self._enrich_batch(all_leads)

        # Phase 4: Quality gate
        if progress_callback:
            progress_callback("Applying quality filters...", 75)
        quality_leads = self._quality_gate(enriched)

        # Phase 5: Score + outreach
        if progress_callback:
            progress_callback("Scoring leads against ICP...", 85)
        for lead in quality_leads:
            lead['icp_score'] = score_lead(lead)
            lead['outreach_draft'] = generate_outreach(lead)

        quality_leads.sort(key=lambda x: x['icp_score'], reverse=True)

        if progress_callback:
            progress_callback(f"Done! {len(quality_leads)} quality leads generated.", 100)
        return quality_leads

    # ─── WEB SEARCH ───────────────────────────────────────────────────────
    def _web_search(self, niche, max_queries, results_per_query, progress_callback):
        queries = WEB_QUERIES.get(niche, WEB_QUERIES['brand_cgi'])
        selected = random.sample(queries, min(max_queries, len(queries)))
        leads = []

        for i, query in enumerate(selected):
            if progress_callback:
                progress_callback(f"Web search: {query[:50]}...", 5 + (i / len(selected)) * 25)
            try:
                results = DDGS().text(query, max_results=results_per_query, region='wt-wt')
                logger.info(f"Web '{query}' → {len(results or [])} results")
                for r in (results or []):
                    lead = self._process_web_result(r, niche, query)
                    if lead and lead['domain'] not in self.found_domains:
                        self.found_domains.add(lead['domain'])
                        leads.append(lead)
                time.sleep(random.uniform(2.5, 4.5))
            except Exception as e:
                logger.error(f"Web search error '{query}': {e}")
                time.sleep(3)
        return leads

    # ─── MAPS SEARCH ──────────────────────────────────────────────────────
    def _maps_search(self, niche, progress_callback):
        categories = MAPS_QUERIES.get(niche, [])
        if not categories:
            return []

        # Pick 3 international cities + 1 Indian city
        intl_cities = random.sample(MAPS_CITIES, min(3, len(MAPS_CITIES)))
        india_cities = random.sample(MAPS_CITIES_INDIA, 1)
        cities = intl_cities + india_cities

        # Pick 2 categories
        selected_cats = random.sample(categories, min(2, len(categories)))
        leads = []

        for cat in selected_cats:
            for city in cities:
                if progress_callback:
                    progress_callback(f"Maps: {cat} in {city}...", 35)
                try:
                    results = DDGS().maps(f"{cat} {city}", max_results=8)
                    for r in (results or []):
                        lead = self._process_maps_result(r, niche, cat, city)
                        if lead and lead['domain'] not in self.found_domains:
                            self.found_domains.add(lead['domain'])
                            leads.append(lead)
                    time.sleep(random.uniform(2, 4))
                except Exception as e:
                    logger.error(f"Maps search error '{cat} {city}': {e}")
                    time.sleep(2)
        return leads

    # ─── PROCESS RESULTS ──────────────────────────────────────────────────
    def _process_web_result(self, result, niche, query):
        url = result.get('href', '')
        if not url:
            return None
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').lower()
        if any(s in domain for s in SKIP_DOMAINS):
            return None
        company_name = self._extract_company_name(result.get('title', ''), domain)
        return {
            'company_name': company_name,
            'website': f"{parsed.scheme}://{parsed.netloc}",
            'domain': domain,
            'contact_name': '', 'contact_role': '',
            'contact_email': '', 'phone_number': '',
            'linkedin_url': '', 'instagram_url': '',
            'niche': niche, 'location': '', 'country': '',
            'description': (result.get('body', '') or '')[:500],
            'signals': [], 'icp_score': 0, 'stage': 'research',
            'outreach_draft': '', 'notes': '',
            'source': f'Web: "{query[:60]}"',
        }

    def _process_maps_result(self, result, niche, category, city):
        url = result.get('url', '')
        title = result.get('title', '')
        if not title:
            return None

        domain = ''
        website = ''
        if url:
            parsed = urlparse(url if url.startswith('http') else f'https://{url}')
            domain = parsed.netloc.replace('www.', '').lower()
            website = f"{parsed.scheme}://{parsed.netloc}"
            if any(s in domain for s in SKIP_DOMAINS):
                return None
        else:
            domain = title.lower().replace(' ', '').replace(',', '')[:30]

        phone = result.get('phone', '') or ''
        address = result.get('address', '') or ''
        city_r = result.get('city', '') or city
        state = result.get('state', '') or ''
        country_r = result.get('country', '') or ''
        location = ', '.join(filter(None, [address[:100], city_r, state, country_r]))

        country = self._detect_country(location + ' ' + city)

        return {
            'company_name': title,
            'website': website, 'domain': domain,
            'contact_name': '', 'contact_role': '',
            'contact_email': '', 'phone_number': phone,
            'linkedin_url': '', 'instagram_url': '',
            'niche': niche, 'location': location, 'country': country,
            'description': (result.get('desc', '') or '')[:500],
            'signals': [f'Found via Maps in {city}'],
            'icp_score': 0, 'stage': 'research',
            'outreach_draft': '', 'notes': '',
            'source': f'Maps: "{category}" in {city}',
        }

    # ─── ENRICHMENT ───────────────────────────────────────────────────────
    def _enrich_batch(self, leads, max_workers=4):
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
        website = lead.get('website', '')
        if not website:
            return lead
        try:
            # Page 1: Homepage
            resp = self.session.get(website, timeout=8, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            # Emails from homepage
            emails = self._extract_emails(resp.text, lead['domain'])
            if emails:
                lead['contact_email'] = emails[0]
                if len(emails) > 1:
                    lead['signals'].append(f"Contacts: {', '.join(emails[:3])}")

            # Phone from homepage
            phones = self._extract_phones(soup, resp.text)
            if phones and not lead['phone_number']:
                lead['phone_number'] = phones[0]

            # Meta description
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta and meta.get('content'):
                lead['description'] = meta['content'][:500]

            # Better company name from title
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                better = self._extract_company_name(title_tag.string.strip(), lead['domain'])
                if 0 < len(better) < len(lead.get('company_name', '') or 'x' * 100):
                    lead['company_name'] = better

            # Social links
            self._extract_social_links(soup, lead)

            # Location + country
            loc = self._extract_location(soup)
            if loc and not lead['location']:
                lead['location'] = loc
            if not lead['country']:
                text = soup.get_text(separator=' ', strip=True)[:5000]
                lead['country'] = self._detect_country(text + ' ' + lead.get('location', ''))

            # Business signals
            lead['signals'].extend(self._extract_signals(soup, resp.text))

            # Page 2: Contact page
            self._scrape_subpage(website, soup, lead, ['contact', 'reach', 'get-in-touch', 'connect'])
            time.sleep(random.uniform(0.3, 0.8))

            # Page 3: About/Team page
            self._scrape_team_page(website, soup, lead)
            time.sleep(random.uniform(0.3, 0.8))

        except requests.RequestException as e:
            logger.debug(f"Could not fetch {website}: {e}")
        except Exception as e:
            logger.debug(f"Error enriching {website}: {e}")
        return lead

    def _scrape_subpage(self, base_url, soup, lead, keywords):
        """Find and scrape a subpage (contact, about, etc.) for emails/phones."""
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            if any(k in href or k in text for k in keywords):
                full_url = urljoin(base_url, link['href'])
                try:
                    r = self.session.get(full_url, timeout=6)
                    if r.ok:
                        domain = urlparse(base_url).netloc.replace('www.', '')
                        emails = self._extract_emails(r.text, domain)
                        if emails and not lead['contact_email']:
                            lead['contact_email'] = emails[0]
                        sub_soup = BeautifulSoup(r.text, 'lxml')
                        phones = self._extract_phones(sub_soup, r.text)
                        if phones and not lead['phone_number']:
                            lead['phone_number'] = phones[0]
                    return
                except Exception:
                    pass

    def _scrape_team_page(self, base_url, soup, lead):
        """Scrape about/team page for decision-maker names and roles."""
        team_keywords = ['about', 'team', 'people', 'leadership', 'founders', 'our-team']
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text(strip=True).lower()
            if any(k in href or k in text for k in team_keywords):
                full_url = urljoin(base_url, link['href'])
                try:
                    r = self.session.get(full_url, timeout=6)
                    if r.ok:
                        team_soup = BeautifulSoup(r.text, 'lxml')
                        name, role = self._extract_team_member(team_soup)
                        if name and not lead['contact_name']:
                            lead['contact_name'] = name
                        if role and not lead['contact_role']:
                            lead['contact_role'] = role
                        if not lead['contact_email']:
                            domain = urlparse(base_url).netloc.replace('www.', '')
                            emails = self._extract_emails(r.text, domain)
                            if emails:
                                lead['contact_email'] = emails[0]
                    return
                except Exception:
                    pass

    def _extract_team_member(self, soup):
        """Extract a decision-maker name and role from a team/about page."""
        text = soup.get_text(separator='\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(t in line_lower for t in DECISION_MAKER_TITLES):
                if len(line) < 80:
                    # This line might be a role, check previous line for name
                    if i > 0 and len(lines[i-1]) < 50 and not any(c.isdigit() for c in lines[i-1]):
                        return lines[i-1].strip(), line.strip()
                    # Or check next line
                    if i + 1 < len(lines) and len(lines[i+1]) < 50:
                        return lines[i+1].strip(), line.strip()
                    # Name might be in the same line: "John Doe - CEO"
                    for sep in [' - ', ' | ', ' — ', ', ', ' – ']:
                        if sep in line:
                            parts = line.split(sep)
                            if len(parts) == 2:
                                p0, p1 = parts[0].strip(), parts[1].strip()
                                if any(t in p1.lower() for t in DECISION_MAKER_TITLES):
                                    return p0, p1
                                if any(t in p0.lower() for t in DECISION_MAKER_TITLES):
                                    return p1, p0
        return '', ''

    # ─── EXTRACTORS ───────────────────────────────────────────────────────
    def _extract_emails(self, html_text, domain):
        pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
        raw = re.findall(pattern, html_text)
        valid, seen = [], set()
        for e in raw:
            e = e.lower().strip('.')
            if e in seen:
                continue
            seen.add(e)
            ed = e.split('@')[1]
            if any(bl in ed for bl in EMAIL_BLACKLIST):
                continue
            if ed.endswith(('.png', '.jpg', '.gif', '.svg', '.css', '.js')):
                continue
            valid.append(e)
        same = [e for e in valid if domain in e]
        other = [e for e in valid if domain not in e]
        return (same + other)[:5]

    def _extract_phones(self, soup, html_text):
        """Extract phone numbers from tel: links and page text."""
        phones = []
        # tel: links (most reliable)
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('tel:'):
                phone = href.replace('tel:', '').strip().replace('%20', ' ')
                if len(re.sub(r'\D', '', phone)) >= 7:
                    phones.append(phone)
        # Regex on visible text
        text = soup.get_text(separator=' ', strip=True)
        phone_pattern = r'(?:\+\d{1,3}[\s.\-]?)?\(?\d{2,4}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}'
        for match in re.findall(phone_pattern, text):
            digits = re.sub(r'\D', '', match)
            if 7 <= len(digits) <= 15 and match not in phones:
                phones.append(match.strip())
        return phones[:3]

    def _extract_social_links(self, soup, lead):
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            if 'linkedin.com/company' in href and not lead['linkedin_url']:
                lead['linkedin_url'] = link['href']
            elif 'instagram.com/' in href and not lead['instagram_url']:
                ig = link['href']
                if 'instagram.com/p/' not in ig.lower():
                    lead['instagram_url'] = ig

    def _extract_location(self, soup):
        text = soup.get_text(separator=' ', strip=True)[:5000].lower()
        for city in INTL_CITIES:
            if city in text:
                return city.title()
        for city in INDIAN_CITIES:
            if city in text:
                return f"{city.title()}, India"
        return ''

    def _detect_country(self, text):
        text_lower = text.lower()
        for country, keywords in COUNTRY_MAP.items():
            if any(kw in text_lower for kw in keywords):
                return country
        return ''

    def _extract_signals(self, soup, html_text):
        signals = []
        t = html_text.lower()
        if any(x in t for x in ['careers', "we're hiring", 'join our team', 'open positions']):
            signals.append('Hiring actively (growth signal)')
        if any(x in t for x in ['our clients', 'trusted by', 'worked with', 'brands we']):
            signals.append('Has existing clients')
        if any(x in t for x in ['portfolio', 'showreel', 'our work', 'case study']):
            signals.append('Active portfolio')
        if any(x in t for x in ['shop now', 'add to cart', 'buy now', 'shopify', 'woocommerce']):
            signals.append('Active e-commerce')
        if any(x in t for x in ['2025', '2026', 'latest', 'new launch', 'coming soon']):
            signals.append('Recent activity detected')
        if any(x in t for x in ['funded', 'series a', 'series b', 'raised', 'investment']):
            signals.append('Funded company (budget signal)')
        if any(x in t for x in ['award', 'winning', 'recognized', 'featured in']):
            signals.append('Award/recognition')
        return signals[:5]

    def _extract_company_name(self, title, domain):
        for sep in [' - ', ' | ', ' — ', ' :: ', ' – ']:
            if sep in title:
                title = title.split(sep)[0].strip()
                break
        if len(title) > 60 or not title:
            title = domain.split('.')[0].replace('-', ' ').replace('_', ' ').title()
        return title

    # ─── QUALITY GATE ─────────────────────────────────────────────────────
    def _quality_gate(self, leads):
        """Filter out leads that are too low quality to be useful."""
        quality = []
        for lead in leads:
            has_contact = bool(lead.get('contact_email') or lead.get('phone_number'))
            has_website = bool(lead.get('website'))
            has_description = len(lead.get('description', '')) > 20
            # Keep lead if it has contact info OR (has website AND description)
            if has_contact or (has_website and has_description):
                quality.append(lead)
        logger.info(f"Quality gate: {len(leads)} → {len(quality)} leads")
        return quality
