"""
F4Leads ICP Scorer v2 — International D2C focus.

Scoring priorities (updated):
  - International D2C brands score HIGHEST on geography
  - India is fallback only
  - Contact info (email + phone) is critical
  - No-contact leads are penalized
"""

import re

# Scoring weights (total: 100)
WEIGHTS = {
    'niche_relevance': 18,
    'has_email': 18,
    'has_phone': 10,
    'has_signals': 12,
    'location_fit': 12,
    'description_quality': 8,
    'active_project': 8,
    'decision_maker': 8,
    'website_quality': 6,
}

NICHE_KEYWORDS = {
    'brand_cgi': [
        'brand', 'd2c', 'dtc', 'direct to consumer', 'fmcg', 'consumer', 'product',
        'ecommerce', 'e-commerce', 'skincare', 'cosmetic', 'fashion',
        'lifestyle', 'organic', 'beauty', 'startup', 'marketing',
        'advertising', 'campaign', 'launch', 'digital', 'shopify',
        'wellness', 'premium', 'luxury', 'sustainable',
    ],
    'ott_film': [
        'production', 'film', 'movie', 'series', 'ott', 'vfx', 'visual effects',
        'post production', 'animation', 'streaming', 'netflix', 'amazon prime',
        'disney', 'hotstar', 'sony', 'zee', 'jio', 'bollywood', 'cinema',
        'short film', 'documentary', 'content', 'studio',
    ],
    'archviz': [
        'architecture', 'architect', 'real estate', 'property', 'interior',
        'design', 'visualization', 'rendering', '3d render', 'walkthrough',
        'construction', 'developer', 'housing', 'residential', 'commercial',
        'building', 'infrastructure',
    ],
    'gaming': [
        'game', 'gaming', 'indie', 'mobile game', 'game dev', 'unity',
        'unreal', 'game art', '3d art', 'game design', 'studio', 'esports',
        'metaverse', 'virtual', 'interactive',
    ],
    'product_viz': [
        'product', '3d render', 'visualization', 'cgi', 'product photo',
        'ecommerce', 'amazon', 'packaging', 'industrial', 'manufacturer',
        'catalog', '360', 'spin', 'animation',
    ],
}

DECISION_MAKER_TITLES = [
    'founder', 'co-founder', 'ceo', 'cto', 'cmo', 'coo',
    'director', 'head', 'vp', 'vice president', 'manager',
    'lead', 'chief', 'owner', 'partner', 'president',
    'marketing', 'creative', 'production', 'brand',
]

# High-value international markets
HIGH_VALUE_COUNTRIES = ['United States', 'United Kingdom', 'UAE', 'Australia', 'Canada', 'Germany', 'France', 'Netherlands', 'Sweden', 'Singapore']


def score_lead(lead):
    """Score a lead 0-100 against AtmonFX's ICP. International D2C focus."""
    total = 0
    niche = lead.get('niche', 'brand_cgi')

    total += _score_niche_relevance(lead, niche)
    total += _score_email(lead)
    total += _score_phone(lead)
    total += _score_signals(lead)
    total += _score_location(lead)
    total += _score_description(lead)
    total += _score_active_project(lead)
    total += _score_decision_maker(lead)
    total += _score_website(lead)

    # Penalty: no contact info at all
    if not lead.get('contact_email') and not lead.get('phone_number'):
        total = max(0, total - 10)

    return min(100, max(0, total))


def _score_niche_relevance(lead, niche):
    keywords = NICHE_KEYWORDS.get(niche, [])
    if not keywords:
        return 9
    text = f"{lead.get('company_name', '')} {lead.get('description', '')}".lower()
    signals_text = ' '.join(lead.get('signals', [])).lower()
    combined = text + ' ' + signals_text
    matches = sum(1 for kw in keywords if kw in combined)
    ratio = matches / len(keywords)
    if ratio > 0.3: return 18
    if ratio > 0.2: return 14
    if ratio > 0.1: return 10
    if ratio > 0.05: return 6
    return 3


def _score_email(lead):
    email = lead.get('contact_email', '')
    if not email:
        return 0
    generic = ['info@', 'contact@', 'hello@', 'support@', 'admin@', 'sales@', 'team@', 'office@']
    if any(email.lower().startswith(p) for p in generic):
        return 12  # Generic but still useful
    return 18  # Personal email = gold


def _score_phone(lead):
    if lead.get('phone_number'):
        return 10
    return 0


def _score_signals(lead):
    signals = lead.get('signals', [])
    if not signals:
        return 0
    score = min(12, len(signals) * 3)
    high_value = ['Hiring actively', 'Recent activity', 'Active e-commerce', 'Has existing clients', 'Funded company', 'Award']
    for s in signals:
        if any(hv in s for hv in high_value):
            score = min(12, score + 2)
    return score


def _score_location(lead):
    """International = highest. India = fallback (lower score)."""
    country = lead.get('country', '').strip()
    location = lead.get('location', '').lower()
    desc = lead.get('description', '').lower()
    combined = f"{country} {location} {desc}".lower()

    # High-value international market
    if country in HIGH_VALUE_COUNTRIES:
        return 12

    # Known international location
    intl_signals = ['usa', 'united states', 'uk', 'london', 'new york', 'dubai',
                    'sydney', 'berlin', 'paris', 'toronto', 'singapore', 'amsterdam']
    if any(s in combined for s in intl_signals):
        return 12

    # Any international signal
    if country and country != 'India':
        return 10

    # India (fallback tier)
    if 'india' in combined or country == 'India':
        return 6

    # Unknown
    return 4


def _score_description(lead):
    desc = lead.get('description', '')
    if not desc:
        return 0
    length = len(desc)
    if length > 200: return 8
    if length > 100: return 6
    if length > 50: return 3
    return 1


def _score_active_project(lead):
    text = f"{lead.get('description', '')} {' '.join(lead.get('signals', []))}".lower()
    words = ['launch', 'new', 'latest', '2025', '2026', 'upcoming', 'coming soon',
             'campaign', 'release', 'production', 'developing', 'building',
             'funded', 'raised', 'series', 'expansion']
    matches = sum(1 for w in words if w in text)
    if matches >= 3: return 8
    if matches >= 2: return 5
    if matches >= 1: return 3
    return 0


def _score_decision_maker(lead):
    role = lead.get('contact_role', '').lower()
    name = lead.get('contact_name', '')
    if role and any(t in role for t in DECISION_MAKER_TITLES):
        return 8
    if role:
        return 4
    if name:
        return 2
    return 0


def _score_website(lead):
    domain = lead.get('domain', '')
    if not domain:
        return 0
    if any(domain.endswith(t) for t in ['.com', '.co', '.io', '.co.uk', '.com.au']):
        return 6
    if any(domain.endswith(t) for t in ['.in', '.de', '.fr', '.nl', '.se', '.ae']):
        return 5
    return 3


def get_score_breakdown(lead):
    """Return a detailed breakdown of the ICP score for a lead."""
    niche = lead.get('niche', 'brand_cgi')
    return {
        'niche_relevance': _score_niche_relevance(lead, niche),
        'has_email': _score_email(lead),
        'has_phone': _score_phone(lead),
        'has_signals': _score_signals(lead),
        'location_fit': _score_location(lead),
        'description_quality': _score_description(lead),
        'active_project': _score_active_project(lead),
        'decision_maker': _score_decision_maker(lead),
        'website_quality': _score_website(lead),
    }


def get_score_label(score):
    """Return a human-readable label for a score."""
    if score >= 85:
        return 'hot'
    elif score >= 70:
        return 'warm'
    elif score >= 50:
        return 'cool'
    else:
        return 'cold'
