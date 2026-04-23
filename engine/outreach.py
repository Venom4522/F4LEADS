"""
F4Leads Outreach Generator — Template-based personalized outreach.
No API key needed. Uses AtmonFX's proven templates with smart variable substitution.
"""

import re
import random

# ─── OUTREACH TEMPLATES ──────────────────────────────────────────────────────

TEMPLATES = {
    'brand_cgi': {
        'email': {
            'subject': 'What if {product_ref} looked this good on screen?',
            'body': """Hi {first_name},

I came across {company}'s work — {hook}. Sharp direction, but I kept thinking: what would a fully CG version look like?

We're AtmonFX, a specialized CGI & VFX studio out of India. We create photorealistic product commercials, brand films, and motion visuals for D2C and consumer brands — work that would typically cost 10x more from a production house, done at an agency-friendly budget.

We actually built a speculative spot for a product in your category — I'd love to share it with you. Takes 90 seconds to watch.

Worth a quick 15-min call this week?

Best,
Dev
Co-Founder, AtmonFX
dev@atmonfx.com | atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — saw {company}'s recent {hook}. Clean work.

Quick context: I'm Dev from AtmonFX, a CGI studio in India. We build photorealistic product visuals for D2C brands at a fraction of what a production house charges.

We made a spec CGI spot for a brand in your space — happy to share if relevant. No pitch, just good work.

Worth a look?""",
        },
    },

    'ott_film': {
        'email': {
            'subject': 'VFX partner for {company}\'s next project?',
            'body': """Hi {first_name},

I came across {company} — {hook}. Compelling work.

Quick context: I'm Dev from AtmonFX, a CGI & VFX studio in India. We specialize in VFX for OTT series and film — environments, creature work, compositing, title sequences.

We've been building our reel specifically for episodic content. If you ever need a reliable, fast-turnaround VFX partner for any part of your pipeline, I'd love to show you what we can do.

No pitch — just happy to share our work if it's relevant.

Best,
Dev
Co-Founder, AtmonFX
dev@atmonfx.com | atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — {hook}.

I'm Dev from AtmonFX, a CGI studio in India. We specialize in VFX for OTT series — environments, creature work, compositing.

If you ever need a fast-turnaround VFX partner, I'd love to show you our reel. Worth a look?""",
        },
    },

    'archviz': {
        'email': {
            'subject': 'Real-time walkthroughs > static renders (here\'s why)',
            'body': """Hi {first_name},

Most ArchViz studios deliver the same thing: static renders, maybe a pre-rendered flythrough. Clients are increasingly expecting more.

We're AtmonFX — we build real-time interactive walkthroughs in Unreal Engine. Your clients can explore a space in real time, change materials on the fly, and experience lighting at different times of day — all before a single brick is laid.

This shortens approval cycles, reduces revision rounds, and gives you a serious competitive edge over studios delivering static images.

We built a sample walkthrough for a residential property — I can send you a recorded version, or share the interactive file if you'd like to explore it.

Interested?

Dev | AtmonFX
dev@atmonfx.com | atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — saw {company}'s work in {hook}. Clean renders.

Quick question: have you explored real-time interactive walkthroughs in Unreal Engine? Clients can change materials, lighting, and explore spaces live — before construction begins.

We're AtmonFX. We built a sample project I'd love to share. Interested?""",
        },
    },

    'gaming': {
        'email': {
            'subject': '3D art support for {company}?',
            'body': """Hi {first_name},

I came across {company} — {hook}. Interesting project.

We're AtmonFX, a 3D art and CGI studio based in India. We support indie and mid-size studios with game-ready assets — character modeling, environment work, props — on a project or retainer basis.

Our pipeline runs on Blender, optimized for game engine export (Unity/Unreal). Fast turnaround, consistent quality, and we slot into your existing pipeline without overhead.

If you're looking for reliable 3D art support, I'd love to show you some of our work.

Best,
Dev
Co-Founder, AtmonFX
dev@atmonfx.com | atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — saw {company}'s work. {hook}.

I'm Dev from AtmonFX — we do 3D art and game-ready assets (Blender pipeline → Unity/Unreal). We support indie studios on project or retainer basis.

If you need reliable 3D art support, happy to share our portfolio. Worth a look?""",
        },
    },

    'product_viz': {
        'email': {
            'subject': 'Studio-quality product visuals — without the studio',
            'body': """Hi {first_name},

I noticed {company}'s product line — {hook}. Great products deserve premium visuals.

We're AtmonFX, a CGI studio in India that creates studio-quality product renders for e-commerce, advertising, and packaging. 360-degree spins, exploded views, lifestyle shots — all done in 3D, no physical photoshoot needed.

The result: consistent, pixel-perfect visuals for every SKU, at a fraction of traditional photography costs. And we can update angles, materials, or backgrounds instantly whenever you need a refresh.

Want to see a few before/after examples from our recent work?

Best,
Dev
Co-Founder, AtmonFX
dev@atmonfx.com | atmonfx.com""",
        },
        'linkedin': {
            'body': """Hi {first_name} — {company}'s product line caught my eye. {hook}.

I'm Dev from AtmonFX. We create studio-quality 3D product renders — e-commerce, ads, packaging. No physical shoot needed, pixel-perfect results.

Happy to share some examples if relevant. Worth a look?""",
        },
    },
}

# Follow-up templates
FOLLOWUP_TEMPLATES = {
    'day4': {
        'subject': 'Re: {original_subject}',
        'body': """Hi {first_name},

Just circling back on my note from a few days ago.

In case it got buried — I had shared that we'd built a speculative CGI spot relevant to {company}'s category. Happy to send it across directly if a link is easier than a call.

No pressure either way.

Dev | AtmonFX""",
    },
    'day10': {
        'subject': 'Something relevant for {company}',
        'body': """Hi {first_name},

Won't keep nudging — this is the last one.

I made a short breakdown video showing exactly how we'd approach a CGI campaign for a brand like {company}. Covers: concept → 3D build → lighting → final comp. About 4 minutes.

If this sparks any interest for upcoming projects, I'd love to chat. If not, totally understand.

Dev
AtmonFX | atmonfx.com""",
    },
}

# Hook generators by niche
HOOKS = {
    'brand_cgi': [
        "the brand identity is solid",
        "the product line looks premium",
        "the latest campaign caught my eye",
        "your digital presence is strong",
        "the product photography is clean",
    ],
    'ott_film': [
        "looks like a compelling production",
        "the slate looks interesting this year",
        "impressive body of work",
        "the production quality stands out",
    ],
    'archviz': [
        "architectural visualization",
        "the design portfolio is clean",
        "the rendering work is solid",
        "the project portfolio stands out",
    ],
    'gaming': [
        "Interesting game concept",
        "the art style is distinct",
        "the development looks promising",
        "interesting project in the pipeline",
    ],
    'product_viz': [
        "Great product design",
        "the product line looks premium",
        "clean product presentation",
        "solid product catalog",
    ],
}


def generate_outreach(lead, channel='email', template_type=None):
    """
    Generate a personalized outreach message for a lead.
    No API needed — uses smart template substitution.
    """
    niche = lead.get('niche', 'brand_cgi')
    template_type = template_type or niche

    templates = TEMPLATES.get(template_type, TEMPLATES['brand_cgi'])
    template = templates.get(channel, templates.get('email', {}))

    if not template:
        return ''

    # Build substitution variables
    company = lead.get('company_name', 'your company')
    email = lead.get('contact_email', '')
    description = lead.get('description', '')

    # Extract first name from contact or generate a generic one
    first_name = _extract_first_name(lead)

    # Generate a contextual hook
    hook = _generate_hook(lead, niche)

    # Product reference (for subject lines)
    product_ref = company + "'s products" if company else "your product"

    # Build the message
    variables = {
        'first_name': first_name,
        'company': company,
        'hook': hook,
        'product_ref': product_ref,
        'original_subject': f"What if {product_ref} looked this good on screen?",
    }

    body = template.get('body', '')
    for key, value in variables.items():
        body = body.replace('{' + key + '}', value)

    # Include subject for emails
    if channel == 'email' and 'subject' in template:
        subject = template['subject']
        for key, value in variables.items():
            subject = subject.replace('{' + key + '}', value)
        return f"Subject: {subject}\n\n{body}"

    return body


def generate_followup(lead, followup_type='day4'):
    """Generate a follow-up message."""
    template = FOLLOWUP_TEMPLATES.get(followup_type, FOLLOWUP_TEMPLATES['day4'])

    company = lead.get('company_name', 'your company')
    first_name = _extract_first_name(lead)
    product_ref = company + "'s products" if company else "your product"

    variables = {
        'first_name': first_name,
        'company': company,
        'original_subject': f"What if {product_ref} looked this good on screen?",
    }

    subject = template.get('subject', '')
    body = template.get('body', '')

    for key, value in variables.items():
        subject = subject.replace('{' + key + '}', value)
        body = body.replace('{' + key + '}', value)

    return f"Subject: {subject}\n\n{body}"


def _extract_first_name(lead):
    """Extract a first name from the lead data, or return a placeholder."""
    name = lead.get('contact_name', '').strip()
    if name:
        return name.split()[0]

    # Try to extract from email
    email = lead.get('contact_email', '').strip()
    if email and '@' in email:
        local_part = email.split('@')[0]
        # Check if it's a real name (not info@, contact@, etc.)
        generic = ['info', 'contact', 'hello', 'support', 'admin', 'sales',
                    'team', 'office', 'mail', 'enquiry', 'inquiry']
        if local_part.lower() not in generic:
            # Try to extract a name (e.g., john.doe → John)
            parts = re.split(r'[._\-]', local_part)
            if parts and len(parts[0]) > 1:
                return parts[0].capitalize()

    return 'there'  # Fallback: "Hi there"


def _generate_hook(lead, niche):
    """Generate a contextual hook based on lead data."""
    description = lead.get('description', '')
    signals = lead.get('signals', [])

    # Try to create a hook from the description
    if description and len(description) > 30:
        # Extract a meaningful phrase from the description
        desc_lower = description.lower()

        # Look for specific mentions
        if 'launch' in desc_lower or 'new' in desc_lower:
            return "the recent launch looks promising"
        if 'award' in desc_lower or 'winning' in desc_lower:
            return "congrats on the recognition"
        if any(sig in desc_lower for sig in ['series', 'season', 'episode']):
            return "the production looks compelling"

    # Use signals if available
    if signals:
        if any('Hiring' in s for s in signals):
            return "looks like you're scaling up"
        if any('Active portfolio' in s for s in signals):
            return "the portfolio work stands out"
        if any('Recent activity' in s for s in signals):
            return "looks like an exciting period"

    # Fallback to niche-specific hooks
    hooks = HOOKS.get(niche, HOOKS['brand_cgi'])
    return random.choice(hooks)


def get_available_templates():
    """Return available template types and channels."""
    result = {}
    for niche, channels in TEMPLATES.items():
        result[niche] = list(channels.keys())
    return result


def get_template_preview(niche, channel='email'):
    """Get a raw template preview (with placeholders visible)."""
    templates = TEMPLATES.get(niche, TEMPLATES['brand_cgi'])
    template = templates.get(channel, {})
    return template.get('body', '')
