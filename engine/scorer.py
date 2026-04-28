"""
F4Leads ICP Scorer v3 — Prioritizes leads ACTIVELY looking for CGI/VFX.
Key changes:
- Intent-based leads score higher
- Verified funding/budget signals score highest
- Contact info is CRITICAL (no email = penalty)
- Quality over quantity
"""

import re

# Scoring weights (total: 100)
WEIGHTS = {
    'intent_signal': 25,      # Looking for CGI/VFX services
    'has_email': 20,           # Email is critical
    'has_phone': 8,            # Phone is good
    'verified_brand': 15,       # Verified D2C brand with funding
    'budget_signal': 12,       # Funding/hiring/budget indicators
    'niche_relevance': 8,       # Matches AtmonFX services
    'decision_maker': 6,         # Has decision maker info
    'location': 6,             # High-value market
}

# Intent keywords: leads ACTIVELY looking for CGI/VFX services
INTENT_KEYWORDS = [
    'need', 'looking for', 'hiring', 'required', 'wanted',
    'quote', 'estimate', 'budget', 'project',
    'freelancer', 'contractor', 'studio', 'service',
    'outsource', 'subcontract', 'partner',
    'request for proposal', 'rfp', 'brief',
    '3D artist', '3D animator', 'cgi artist', 'vfx artist',
    'visualization', 'rendering', 'walkthrough',
]

# Budget signals: company HAS MONEY
BUDGET_SIGNALS = [
    'funded', 'raised', 'series a', 'series b', 'investment',
    'hiring', 'we\'re hiring', 'open positions', 'join our team',
    'budget', 'allocated', 'investment',
    'expanding', 'scaling', 'growth',
]

# Verified D2C brands (from funding news)
VERIFIED_BRANDS = [
    'clayco', 'antinorm', 'unbound', 'salty', 'bluetyga',
    'mamaearth', 'minimalist', 'sugar cosmetics', 'myglamm',
    'dot & key', 'the man company', 'beardo',
    'banyan', 'sleepyowl', 'boatlift',
]

# High-value markets
HIGH_VALUE_MARKETS = [
    'united states', 'usa', 'uk', 'united kingdom',
    'uae', 'dubai', 'australia', 'canada', 'germany',
    'france', 'netherlands', 'sweden', 'singapore',
    'new york', 'los angeles', 'san francisco', 'london',
]

# Decision maker titles
DECISION_MAKER_TITLES = [
    'founder', 'co-founder', 'ceo', 'cto', 'cmo', 'coo',
    'director', 'head', 'vp', 'vice president',
    'manager', 'lead', 'chief', 'owner', 'partner',
]

# Niche relevance
NICHE_KEYWORDS = {
    'brand_cgi': [
        'brand', 'd2c', 'dtc', 'direct to consumer', 'fmcg',
        'ecommerce', 'e-commerce', 'skincare', 'cosmetic', 'fashion',
        'lifestyle', 'beauty', 'startup', 'marketing', 'advertising',
        'campaign', 'launch', 'digital', 'shopify', 'wellness',
    ],
    'ott_film': [
        'production', 'film', 'movie', 'series', 'ott',
        'vfx', 'visual effects', 'post production', 'animation',
        'streaming', 'netflix', 'amazon', 'disney', 'hotstar',
    ],
    'archviz': [
        'architecture', 'architect', 'real estate', 'property',
        'interior', 'design', 'visualization', 'rendering',
        'walkthrough', 'construction', 'developer',
    ],
    'gaming': [
        'game', 'gaming', 'indie', 'mobile game', 'unity',
        'unreal', 'game art', '3d art', 'game design',
    ],
    'product_viz': [
        'product', '3d render', 'visualization', 'cgi',
        'ecommerce', 'amazon', 'packaging', 'industrial',
    ],
}


def score_lead(lead):
    """Score a lead 0-100. Prioritizes intent and contact info."""
    total = 0
    niche = lead.get('niche', 'brand_cgi')

    total += _score_intent(lead)
    total += _score_email(lead)
    total += _score_phone(lead)
    total += _score_verified(lead)
    total += _score_budget(lead)
    total += _score_niche(lead, niche)
    total += _score_decision_maker(lead)
    total += _score_location(lead)

    # Critical: No contact = BIG penalty
    if not lead.get('contact_email') and not lead.get('phone_number'):
        total = max(0, total - 15)

    return min(100, max(0, total))


def _score_intent(lead):
    """Score leads actively looking for CGI/VFX services."""
    text = f"{lead.get('description', '')} {lead.get('source', '')}".lower()
    signals = ' '.join(lead.get('signals', [])).lower()
    combined = f"{text} {signals}"
    
    matches = sum(1 for kw in INTENT_KEYWORDS if kw in combined)
    
    # Check if source indicates intent
    source = lead.get('source', '').lower()
    if 'intent' in source or 'job' in source or 'rfp' in source or 'quote' in source:
        matches += 3
    
    if matches >= 4:
        return 25
    if matches >= 2:
        return 18
    if matches >= 1:
        return 10
    return 3


def _score_email(lead):
    """Email is CRITICAL for outreach."""
    email = lead.get('contact_email', '')
    if not email:
        return 0
    
    # Generic emails still count (info@, contact@, etc.)
    return 20


def _score_phone(lead):
    """Phone is useful but not critical."""
    if lead.get('phone_number'):
        return 8
    return 0


def _score_verified(lead):
    """Verified D2C brands with funding."""
    name = lead.get('company_name', '').lower()
    source = lead.get('source', '').lower()
    
    # Verified list
    if 'verified' in source:
        return 15
    
    # Check against known brands
    for brand in VERIFIED_BRANDS:
        if brand in name:
            return 15
    
    return 0


def _score_budget(lead):
    """Company has budget (hiring, funding, etc.)."""
    text = f"{lead.get('description', '')} {' '.join(lead.get('signals', []))}".lower()
    
    matches = sum(1 for s in BUDGET_SIGNALS if s in text)
    
    if matches >= 3:
        return 12
    if matches >= 2:
        return 8
    if matches >= 1:
        return 4
    return 0


def _score_niche(lead, niche):
    """Relevance to AtmonFX services."""
    keywords = NICHE_KEYWORDS.get(niche, [])
    if not keywords:
        return 4
    
    text = f"{lead.get('company_name', '')} {lead.get('description', '')}".lower()
    matches = sum(1 for kw in keywords if kw in text)
    
    if matches >= 4:
        return 8
    if matches >= 2:
        return 5
    if matches >= 1:
        return 2
    return 0


def _score_decision_maker(lead):
    """Has decision maker info."""
    role = lead.get('contact_role', '').lower()
    name = lead.get('contact_name', '')
    
    if role and any(t in role for t in DECISION_MAKER_TITLES):
        return 6
    if role:
        return 3
    if name:
        return 1
    return 0


def _score_location(lead):
    """High-value market."""
    text = f"{lead.get('location', '')} {lead.get('country', '')}".lower()
    
    for market in HIGH_VALUE_MARKETS:
        if market in text:
            return 6
    
    # India is fallback
    if 'india' in text:
        return 3
    
    return 2


def get_score_breakdown(lead):
    """Detailed score breakdown."""
    niche = lead.get('niche', 'brand_cgi')
    return {
        'intent_signal': _score_intent(lead),
        'has_email': _score_email(lead),
        'has_phone': _score_phone(lead),
        'verified_brand': _score_verified(lead),
        'budget_signal': _score_budget(lead),
        'niche_relevance': _score_niche(lead, niche),
        'decision_maker': _score_decision_maker(lead),
        'location': _score_location(lead),
    }


def get_score_label(score):
    """Human-readable label."""
    if score >= 85:
        return 'hot'
    if score >= 70:
        return 'warm'
    if score >= 50:
        return 'cool'
    return 'cold'