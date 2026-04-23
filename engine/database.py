"""
F4Leads Database — SQLite storage for leads, outreach history, and search logs.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'leads.db')


def get_connection():
    """Get a database connection with row_factory set."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            website TEXT,
            domain TEXT,
            contact_name TEXT DEFAULT '',
            contact_role TEXT DEFAULT '',
            contact_email TEXT DEFAULT '',
            phone_number TEXT DEFAULT '',
            linkedin_url TEXT DEFAULT '',
            instagram_url TEXT DEFAULT '',
            niche TEXT DEFAULT 'brand_cgi',
            location TEXT DEFAULT '',
            country TEXT DEFAULT '',
            description TEXT DEFAULT '',
            signals TEXT DEFAULT '[]',
            icp_score INTEGER DEFAULT 0,
            stage TEXT DEFAULT 'research',
            outreach_draft TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            source TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_contacted TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS outreach_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            template_type TEXT,
            channel TEXT DEFAULT 'email',
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'draft',
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            niche TEXT,
            results_count INTEGER DEFAULT 0,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_leads_niche ON leads(niche);
        CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
        CREATE INDEX IF NOT EXISTS idx_leads_icp_score ON leads(icp_score DESC);
        CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(domain);
        CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country);
    """)

    conn.commit()

    # Run migrations for existing databases
    _migrate_db(conn)

    conn.close()


def _migrate_db(conn):
    """Add new columns if they don't exist (safe for existing databases)."""
    migrations = [
        "ALTER TABLE leads ADD COLUMN phone_number TEXT DEFAULT ''",
        "ALTER TABLE leads ADD COLUMN linkedin_url TEXT DEFAULT ''",
        "ALTER TABLE leads ADD COLUMN instagram_url TEXT DEFAULT ''",
        "ALTER TABLE leads ADD COLUMN country TEXT DEFAULT ''",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists


def dict_from_row(row):
    """Convert a sqlite3.Row to a dict, parsing JSON fields."""
    if row is None:
        return None
    d = dict(row)
    if 'signals' in d and isinstance(d['signals'], str):
        try:
            d['signals'] = json.loads(d['signals'])
        except (json.JSONDecodeError, TypeError):
            d['signals'] = []
    return d


# ─── LEAD CRUD ────────────────────────────────────────────────────────────────

def add_lead(lead_data):
    """Insert a new lead. Returns the new lead's ID."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check for duplicate by domain
    domain = lead_data.get('domain', '')
    if domain:
        existing = cursor.execute(
            "SELECT id FROM leads WHERE domain = ?", (domain,)
        ).fetchone()
        if existing:
            conn.close()
            return None  # Duplicate

    signals = lead_data.get('signals', [])
    if isinstance(signals, list):
        signals = json.dumps(signals)

    cursor.execute("""
        INSERT INTO leads (company_name, website, domain, contact_name, contact_role,
            contact_email, phone_number, linkedin_url, instagram_url,
            niche, location, country, description, signals, icp_score, stage,
            outreach_draft, notes, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead_data.get('company_name', 'Unknown'),
        lead_data.get('website', ''),
        domain,
        lead_data.get('contact_name', ''),
        lead_data.get('contact_role', ''),
        lead_data.get('contact_email', ''),
        lead_data.get('phone_number', ''),
        lead_data.get('linkedin_url', ''),
        lead_data.get('instagram_url', ''),
        lead_data.get('niche', 'brand_cgi'),
        lead_data.get('location', ''),
        lead_data.get('country', ''),
        lead_data.get('description', ''),
        signals,
        lead_data.get('icp_score', 0),
        lead_data.get('stage', 'research'),
        lead_data.get('outreach_draft', ''),
        lead_data.get('notes', ''),
        lead_data.get('source', ''),
    ))

    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id


def get_lead(lead_id):
    """Get a single lead by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    return dict_from_row(row)


def get_all_leads(niche=None, stage=None, min_score=None, sort_by='icp_score', order='DESC', limit=200):
    """Get leads with optional filters."""
    conn = get_connection()
    query = "SELECT * FROM leads WHERE 1=1"
    params = []

    if niche and niche != 'all':
        query += " AND niche = ?"
        params.append(niche)
    if stage and stage != 'all':
        query += " AND stage = ?"
        params.append(stage)
    if min_score is not None:
        query += " AND icp_score >= ?"
        params.append(min_score)

    allowed_sort = {'icp_score', 'created_at', 'company_name', 'stage', 'niche'}
    if sort_by not in allowed_sort:
        sort_by = 'icp_score'
    allowed_order = {'ASC', 'DESC'}
    if order.upper() not in allowed_order:
        order = 'DESC'

    query += f" ORDER BY {sort_by} {order} LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]


def update_lead(lead_id, updates):
    """Update a lead's fields."""
    conn = get_connection()
    allowed_fields = {
        'company_name', 'website', 'domain', 'contact_name', 'contact_role',
        'contact_email', 'phone_number', 'linkedin_url', 'instagram_url',
        'niche', 'location', 'country', 'description', 'signals',
        'icp_score', 'stage', 'outreach_draft', 'notes', 'source', 'last_contacted'
    }

    set_parts = []
    params = []
    for key, value in updates.items():
        if key in allowed_fields:
            if key == 'signals' and isinstance(value, list):
                value = json.dumps(value)
            set_parts.append(f"{key} = ?")
            params.append(value)

    if not set_parts:
        conn.close()
        return False

    set_parts.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(lead_id)

    conn.execute(
        f"UPDATE leads SET {', '.join(set_parts)} WHERE id = ?", params
    )
    conn.commit()
    conn.close()
    return True


def delete_lead(lead_id):
    """Delete a lead by ID."""
    conn = get_connection()
    conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()
    return True


def get_stats():
    """Get dashboard statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    total = cursor.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    hot = cursor.execute("SELECT COUNT(*) FROM leads WHERE icp_score >= 85").fetchone()[0]
    warm = cursor.execute("SELECT COUNT(*) FROM leads WHERE icp_score >= 70 AND icp_score < 85").fetchone()[0]
    with_email = cursor.execute("SELECT COUNT(*) FROM leads WHERE contact_email != ''").fetchone()[0]
    with_phone = cursor.execute("SELECT COUNT(*) FROM leads WHERE phone_number != ''").fetchone()[0]

    stages = {}
    for row in cursor.execute("SELECT stage, COUNT(*) as cnt FROM leads GROUP BY stage"):
        stages[row['stage']] = row['cnt']

    niches = {}
    for row in cursor.execute("SELECT niche, COUNT(*) as cnt FROM leads GROUP BY niche"):
        niches[row['niche']] = row['cnt']

    countries = {}
    for row in cursor.execute("SELECT country, COUNT(*) as cnt FROM leads WHERE country != '' GROUP BY country ORDER BY cnt DESC LIMIT 10"):
        countries[row['country']] = row['cnt']

    avg_score = cursor.execute("SELECT AVG(icp_score) FROM leads").fetchone()[0] or 0

    recent = [dict_from_row(r) for r in cursor.execute(
        "SELECT * FROM leads ORDER BY created_at DESC LIMIT 5"
    ).fetchall()]

    hot_leads = [dict_from_row(r) for r in cursor.execute(
        "SELECT * FROM leads WHERE icp_score >= 85 ORDER BY icp_score DESC LIMIT 10"
    ).fetchall()]

    conn.close()

    return {
        'total_leads': total,
        'hot_leads': hot,
        'warm_leads': warm,
        'with_email': with_email,
        'with_phone': with_phone,
        'avg_score': round(avg_score, 1),
        'by_stage': stages,
        'by_niche': niches,
        'by_country': countries,
        'recent': recent,
        'hot_lead_list': hot_leads,
    }


def get_leads_by_stage():
    """Get leads grouped by pipeline stage."""
    conn = get_connection()
    stages = ['research', 'contacted', 'replied', 'in_discussion', 'closed']
    result = {}

    for stage in stages:
        rows = conn.execute(
            "SELECT * FROM leads WHERE stage = ? ORDER BY icp_score DESC", (stage,)
        ).fetchall()
        result[stage] = [dict_from_row(r) for r in rows]

    conn.close()
    return result


def log_search(query, niche, results_count):
    """Log a search query."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO search_history (query, niche, results_count) VALUES (?, ?, ?)",
        (query, niche, results_count)
    )
    conn.commit()
    conn.close()


def add_outreach(lead_id, template_type, channel, content):
    """Log an outreach message."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO outreach_history (lead_id, template_type, channel, content) VALUES (?, ?, ?, ?)",
        (lead_id, template_type, channel, content)
    )
    conn.commit()
    conn.close()


def get_outreach_history(lead_id):
    """Get outreach history for a lead."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM outreach_history WHERE lead_id = ? ORDER BY created_at DESC",
        (lead_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
