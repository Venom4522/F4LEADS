"""
F4Leads Outreach Generator v3 — Contextual, real hooks.
Generates personalized outreach based on ACTUAL lead data.
"""

import re
import random

# ─── TEMPLATES (Updated for better response) ─────────────────────────────────────────

TEMPLATES = {
    'brand_cgi': {
        'email': {
            'subject': 'Quick question about {company}\'s product visuals',
            'body': """Hi {first_name},

Saw {company}'s work — {hook}.

I'm Dev. We create CGI product visuals for D2C brands — photorealistic renders, product animations, brand films.

Quick question: Are you currently working with a 3D/CGI studio for your product visuals, or is this something you might be looking into?

Reason I'm asking: We specialize in exactly this — and have capacity to take on new projects.

Happy to share our portfolio if relevant.

Best,
Dev
dev@atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — saw {company}'s {hook}.

Quick question: working with a CGI studio for product visuals, or looking for options?

We do photorealistic 3D renders + product animations for D2C brands. Happy to share work if relevant.

""",
        },
    },

    'ott_film': {
        'email': {
            'subject': 'VFX support for {company}\'s production?',
            'body': """Hi {first_name},

Saw {company}'s recent production — {hook}.

I'm Dev from AtmonFX. We provide VFX support for film/OTT — environments, compositing, creature work.

Quick question: Do you have a VFX partner for current/future projects, or is this an area you might be looking to outsource?

Happy to share our reel if useful.

Best,
Dev
dev@atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — {hook}.

We provide VFX support for film/OTT. Environments, compositing, creature work.

Looking for a VFX partner, or already have one in place?

""",
        },
    },

    'archviz': {
        'email': {
            'subject': 'Real-time walkthroughs for {company}?',
            'body': """Hi {first_name},

Saw {company}'s work — {hook}.

We build real-time walkthroughs in Unreal Engine — clients can explore spaces live, change materials, lighting.

Quick question: Is real-time something you're offering clients, or would be valuable to add?

Happy to show a quick demo.

Best,
Dev
dev@atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — {hook}.

We do Unreal Engine real-time walkthroughs. Clients explore spaces live, change materials on the fly.

Offering this already, or it's something you'd like to add?

""",
        },
    },

    'gaming': {
        'email': {
            'subject': '3D art support for {company}?',
            'body': """Hi {first_name},

Saw {company}'s project — {hook}.

We provide 3D art support for game studios — assets, characters, environments. Blender pipeline → Unity/Unreal ready.

Quick question: Need additional 3D art support, or your team has it covered?

Happy to share our portfolio.

Best,
Dev
dev@atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — {hook}.

We do game-ready 3D assets (Blender → Unity/Unreal). Need extra art support?

""",
        },
    },

    'product_viz': {
        'email': {
            'subject': '3D product renders for {company}?',
            'body': """Hi {first_name},

Saw {company}'s product line — {hook}.

We create studio-quality 3D product renders — no physical photoshoot needed.

Quick question: Handling product visuals in-house, or is this something you'd consider outsourcing?

Best,
Dev
dev@atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — {hook}.

We do 3D product renders (no physical shoot needed). Handling in-house or looking for options?

""",
        },
    },
}

# ─── HOOK GENERATORS (Based on REAL data) ─────────────────────────────────────────

def _generate_hook(lead):
    """Generate contextual hook from ACTUAL lead data."""
    description = lead.get('description', '')
    signals = lead.get('signals', [])
    company = lead.get('company_name', '')
    source = lead.get('source', '')

    # Priority 1: From description
    if description:
        desc_lower = description.lower()
        
        # Product/category mentions
        if any(w in desc_lower for w in ['skincare', 'beauty', 'cosmetic']):
            return "skincare products look great"
        if any(w in desc_lower for w in ['fashion', 'apparel', 'clothing']):
            return "fashion line"
        if any(w in desc_lower for w in ['food', 'beverage', 'drink']):
            return "product line"
        if any(w in desc_lower for w in ['home', 'furniture', 'decor']):
            return "home products"
        if any(w in desc_lower for w in ['tech', 'gadget', 'electronic']):
            return "tech products"
        
        # Activity signals
        if any(w in desc_lower for w in ['launch', 'new', 'recently']):
            return "recent launch"
        if any(w in desc_lower for w in ['expanding', 'growing', 'scaling']):
            return "scaling up"
    
    # Priority 2: From signals
    if signals:
        for s in signals:
            s_lower = s.lower()
            if 'funded' in s_lower or 'raised' in s_lower:
                return "congrats on the funding"
            if 'hiring' in s_lower:
                return "scaling up"
            if 'verified' in s_lower:
                return "impressive brand"
    
    # Priority 3: From source
    if 'intent' in source.lower():
        return "seeking CGI/VFX services"
    if 'verified' in source.lower():
        return "funded brand"
    
    # Fallback: company type
    if company:
        return f"{company}'s work"
    
    return "your work"


def _extract_first_name(lead):
    """Extract first name from lead."""
    name = lead.get('contact_name', '').strip()
    if name:
        return name.split()[0]

    email = lead.get('contact_email', '').strip()
    if email and '@' in email:
        local = email.split('@')[0]
        generic = ['info', 'contact', 'hello', 'support', 'admin', 'sales', 'team']
        if local.lower() not in generic:
            parts = re.split(r'[._\-]', local)
            if parts and len(parts[0]) > 1:
                return parts[0].capitalize()

    return 'there'


def generate_outreach(lead, channel='email'):
    """Generate personalized outreach message."""
    niche = lead.get('niche', 'brand_cgi')
    templates = TEMPLATES.get(niche, TEMPLATES['brand_cgi'])
    template = templates.get(channel, TEMPLATES['brand_cgi']['email'])

    if not template:
        return ''

    # Build variables
    first_name = _extract_first_name(lead)
    company = lead.get('company_name', 'your company')
    hook = _generate_hook(lead)

    variables = {
        'first_name': first_name,
        'company': company,
        'hook': hook,
    }

    body = template.get('body', '')
    for key, value in variables.items():
        body = body.replace('{' + key + '}', value)

    if channel == 'email' and 'subject' in template:
        subject = template['subject']
        for key, value in variables.items():
            subject = subject.replace('{' + key + '}', value)
        return f"Subject: {subject}\n\n{body}"

    return body


def get_available_templates():
    """Return available template types and channels."""
    result = {}
    for niche, channels in TEMPLATES.items():
        result[niche] = list(channels.keys())
    return result


def get_template_preview(niche, channel='email'):
    """Get a raw template preview."""
    templates = TEMPLATES.get(niche, TEMPLATES['brand_cgi'])
    template = templates.get(channel, {})
    return template.get('body', '')


def generate_followup(lead, followup_type='day4'):
    """Generate follow-up."""
    first_name = _extract_first_name(lead)
    company = lead.get('company_name', 'your company')

    body = f"""Hi {first_name},

Just circling back on my note. No pressure if now's not the right time.

If you ARE looking for a CGI/VFX partner, we'd love to chat.

Best,
Dev
dev@atmonfx.com"""

    subject = f"Re: {company}"
    return f"Subject: {subject}\n\n{body}"