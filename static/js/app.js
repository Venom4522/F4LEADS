/* ═══════════════════════════════════════════════════════════════════════════════
   F4Leads — Frontend Application
   Single-page app with dashboard, leads, pipeline, outreach, and generation.
   ═══════════════════════════════════════════════════════════════════════════════ */

// ── State ────────────────────────────────────────────────────────────────────

const state = {
    currentView: 'dashboard',
    leads: [],
    stats: {},
    pipeline: {},
    selectedLead: null,
    selectedNiche: 'brand_cgi',
    generating: false,
    generationPollTimer: null,
    filters: {
        niche: 'all',
        stage: 'all',
        sort_by: 'icp_score',
        order: 'DESC',
    },
};

const NICHE_LABELS = {
    'brand_cgi': 'Brand CGI',
    'ott_film': 'OTT / Film VFX',
    'archviz': 'ArchViz',
    'gaming': 'Gaming',
    'product_viz': 'Product Viz',
};

const NICHE_ICONS = {
    'brand_cgi': '🎬',
    'ott_film': '🎥',
    'archviz': '🏛️',
    'gaming': '🎮',
    'product_viz': '📦',
};

const STAGE_LABELS = {
    'research': 'Research',
    'contacted': 'Contacted',
    'replied': 'Replied',
    'in_discussion': 'In Discussion',
    'closed': 'Closed',
};


// ── Initialize ───────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupSearch();
    navigate('dashboard');
});


// ── Navigation ───────────────────────────────────────────────────────────────

function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            navigate(view);
        });
    });
}

function navigate(view) {
    state.currentView = view;

    // Update active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });

    // Update title
    const titles = {
        'dashboard': 'Dashboard',
        'leads': 'Leads',
        'pipeline': 'Pipeline',
        'outreach': 'Outreach Studio',
        'generate': 'Generate Leads',
    };
    document.getElementById('page-title').textContent = titles[view] || 'Dashboard';

    // Render view
    switch (view) {
        case 'dashboard': renderDashboard(); break;
        case 'leads': renderLeads(); break;
        case 'pipeline': renderPipeline(); break;
        case 'outreach': renderOutreach(); break;
        case 'generate': renderGenerate(); break;
    }
}

function showGenerateView() {
    navigate('generate');
}


// ── Search ───────────────────────────────────────────────────────────────────

function setupSearch() {
    const search = document.getElementById('global-search');
    let debounce;

    search.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
            if (state.currentView === 'leads') {
                renderLeadTable(search.value.trim());
            }
        }, 300);
    });
}


// ── API Helpers ──────────────────────────────────────────────────────────────

async function api(endpoint, options = {}) {
    const { method = 'GET', body } = options;
    const config = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) config.body = JSON.stringify(body);

    const resp = await fetch(`/api${endpoint}`, config);
    return resp.json();
}


// ── Toast Notifications ──────────────────────────────────────────────────────

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    toast.innerHTML = `<span>${icons[type] || '•'}</span> ${message}`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 200);
    }, 3500);
}


// ── Modal System ─────────────────────────────────────────────────────────────

function showModal(html) {
    const overlay = document.getElementById('modal-overlay');
    const content = document.getElementById('modal-content');
    content.innerHTML = html;
    overlay.style.display = 'flex';

    overlay.onclick = (e) => {
        if (e.target === overlay) closeModal();
    };

    document.addEventListener('keydown', handleEsc);
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
    document.removeEventListener('keydown', handleEsc);
}

function handleEsc(e) {
    if (e.key === 'Escape') closeModal();
}


// ── Score Helpers ────────────────────────────────────────────────────────────

function getScoreClass(score) {
    if (score >= 85) return 'hot';
    if (score >= 70) return 'warm';
    if (score >= 50) return 'cool';
    return 'cold';
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}


// ═══════════════════════════════════════════════════════════════════════════════
// DASHBOARD VIEW
// ═══════════════════════════════════════════════════════════════════════════════

async function renderDashboard() {
    const content = document.getElementById('content-area');
    content.innerHTML = '<div class="loading-state"><div class="spinner"></div> Loading dashboard...</div>';

    const stats = await api('/stats');
    state.stats = stats;

    const byStage = stats.by_stage || {};
    const contacted = (byStage.contacted || 0) + (byStage.replied || 0) +
                      (byStage.in_discussion || 0) + (byStage.closed || 0);

    content.innerHTML = `
        <!-- Stats Cards -->
        <div class="stats-grid">
            <div class="stat-card accent">
                <div class="stat-label">Total Leads</div>
                <div class="stat-value accent">${stats.total_leads || 0}</div>
                <div class="stat-sub">In your pipeline</div>
            </div>
            <div class="stat-card hot">
                <div class="stat-label">Hot Leads</div>
                <div class="stat-value hot">${stats.hot_leads || 0}</div>
                <div class="stat-sub">ICP Score ≥ 85</div>
            </div>
            <div class="stat-card warm">
                <div class="stat-label">Warm Leads</div>
                <div class="stat-value warm">${stats.warm_leads || 0}</div>
                <div class="stat-sub">ICP Score 70–84</div>
            </div>
            <div class="stat-card cyan">
                <div class="stat-label">With Email</div>
                <div class="stat-value cyan">${stats.with_email || 0}</div>
                <div class="stat-sub">Have contact email</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">With Phone</div>
                <div class="stat-value">${stats.with_phone || 0}</div>
                <div class="stat-sub">Have phone number</div>
            </div>
        </div>

        <!-- Dashboard Panels -->
        <div class="dashboard-grid">
            <!-- Hot Leads Panel -->
            <div class="dashboard-panel">
                <div class="dashboard-panel-title">🔥 Hot Leads</div>
                ${renderHotLeadsList(stats.hot_lead_list || [])}
            </div>

            <!-- Niche Distribution -->
            <div class="dashboard-panel">
                <div class="dashboard-panel-title">📊 Niche Distribution</div>
                ${renderNicheBars(stats.by_niche || {})}
            </div>
        </div>

        <!-- Recent Activity -->
        <div style="margin-top: 20px;">
            <div class="dashboard-panel">
                <div class="dashboard-panel-title">⏱️ Recent Leads</div>
                ${renderRecentActivity(stats.recent || [])}
            </div>
        </div>

        ${stats.total_leads === 0 ? `
        <div class="empty-state" style="margin-top: 20px;">
            <div class="empty-state-icon">🚀</div>
            <h3>No leads yet</h3>
            <p>Click "Generate Leads" to start discovering companies that match your ICP.</p>
            <button class="btn btn-primary btn-lg" onclick="showGenerateView()">
                <span>⚡</span> Generate Your First Leads
            </button>
        </div>` : ''}
    `;
}

function renderHotLeadsList(leads) {
    if (!leads.length) {
        return '<div style="color: var(--text-tertiary); font-size: 0.8rem; padding: 12px 0;">No hot leads yet. Generate leads to find high-ICP matches.</div>';
    }

    return `<div class="activity-list">
        ${leads.map(l => `
            <div class="activity-item" style="cursor:pointer;" onclick="showLeadDetail(${l.id})">
                <span class="score-badge ${getScoreClass(l.icp_score)}">${l.icp_score}</span>
                <div class="activity-text">
                    <strong>${escapeHtml(l.company_name)}</strong>
                    ${l.contact_email ? `<br><span style="font-size:0.7rem;color:var(--text-tertiary);">${escapeHtml(l.contact_email)}</span>` : ''}
                </div>
                <span class="niche-tag ${l.niche}">${NICHE_LABELS[l.niche] || l.niche}</span>
            </div>
        `).join('')}
    </div>`;
}

function renderNicheBars(niches) {
    const entries = Object.entries(niches);
    if (!entries.length) {
        return '<div style="color: var(--text-tertiary); font-size: 0.8rem; padding: 12px 0;">No data yet.</div>';
    }

    const max = Math.max(...entries.map(([_, v]) => v), 1);

    return `<div class="niche-bars">
        ${entries.map(([niche, count]) => `
            <div class="niche-bar-row">
                <span class="niche-bar-label">${NICHE_LABELS[niche] || niche}</span>
                <div class="niche-bar-track">
                    <div class="niche-bar-fill ${niche}" style="width: ${(count / max) * 100}%"></div>
                </div>
                <span class="niche-bar-count">${count}</span>
            </div>
        `).join('')}
    </div>`;
}

function renderRecentActivity(recent) {
    if (!recent.length) {
        return '<div style="color: var(--text-tertiary); font-size: 0.8rem; padding: 12px 0;">No recent activity.</div>';
    }

    return `<div class="activity-list">
        ${recent.map(l => `
            <div class="activity-item" style="cursor:pointer;" onclick="showLeadDetail(${l.id})">
                <div class="activity-dot"></div>
                <div class="activity-text">
                    <strong>${escapeHtml(l.company_name)}</strong> added
                </div>
                <span class="niche-tag ${l.niche}" style="font-size:0.62rem;">${NICHE_LABELS[l.niche] || l.niche}</span>
                <span class="activity-time">${timeAgo(l.created_at)}</span>
            </div>
        `).join('')}
    </div>`;
}


// ═══════════════════════════════════════════════════════════════════════════════
// LEADS VIEW
// ═══════════════════════════════════════════════════════════════════════════════

async function renderLeads() {
    const content = document.getElementById('content-area');
    content.innerHTML = `
        <div class="table-controls">
            <select class="filter-select" id="filter-niche" onchange="applyFilters()">
                <option value="all">All Niches</option>
                ${Object.entries(NICHE_LABELS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
            </select>
            <select class="filter-select" id="filter-stage" onchange="applyFilters()">
                <option value="all">All Stages</option>
                ${Object.entries(STAGE_LABELS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
            </select>
            <select class="filter-select" id="filter-sort" onchange="applyFilters()">
                <option value="icp_score">Sort: ICP Score</option>
                <option value="created_at">Sort: Newest</option>
                <option value="company_name">Sort: Company Name</option>
            </select>
            <div style="flex:1;"></div>
            <button class="btn btn-secondary btn-sm" onclick="showAddLeadModal()">+ Add Lead</button>
            <button class="btn btn-primary btn-sm" onclick="showGenerateView()">⚡ Generate</button>
        </div>
        <div id="leads-table-container">
            <div class="loading-state"><div class="spinner"></div> Loading leads...</div>
        </div>
    `;

    await renderLeadTable();
}

async function renderLeadTable(searchQuery = '') {
    const container = document.getElementById('leads-table-container');
    if (!container) return;

    const params = new URLSearchParams({
        niche: state.filters.niche,
        stage: state.filters.stage,
        sort_by: state.filters.sort_by,
        order: state.filters.order,
    });

    const leads = await api(`/leads?${params}`);
    state.leads = leads;

    // Filter by search query
    let filtered = leads;
    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        filtered = leads.filter(l =>
            l.company_name.toLowerCase().includes(q) ||
            (l.contact_email || '').toLowerCase().includes(q) ||
            (l.description || '').toLowerCase().includes(q)
        );
    }

    if (!filtered.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🎯</div>
                <h3>No leads found</h3>
                <p>Try adjusting your filters or generate new leads.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <table class="leads-table">
            <thead>
                <tr>
                    <th>Company</th>
                    <th>Score</th>
                    <th>Niche</th>
                    <th>Stage</th>
                    <th>Contact</th>
                    <th>Country</th>
                    <th>Added</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${filtered.map(lead => {
                    const contactParts = [];
                    if (lead.contact_email) contactParts.push(`<span title="${escapeHtml(lead.contact_email)}">✉️ ${escapeHtml(lead.contact_email.length > 22 ? lead.contact_email.substring(0,20)+'…' : lead.contact_email)}</span>`);
                    if (lead.phone_number) contactParts.push(`<span title="${escapeHtml(lead.phone_number)}">📞 ${escapeHtml(lead.phone_number)}</span>`);
                    const contactHtml = contactParts.length ? contactParts.join('<br>') : '<span style="color:var(--text-tertiary)">—</span>';
                    return `
                    <tr class="${lead.icp_score >= 85 ? 'hot-row' : ''}" onclick="showLeadDetail(${lead.id})" style="cursor:pointer;">
                        <td>${escapeHtml(lead.company_name)}</td>
                        <td><span class="score-badge ${getScoreClass(lead.icp_score)}">${lead.icp_score}</span></td>
                        <td><span class="niche-tag ${lead.niche}">${NICHE_LABELS[lead.niche] || lead.niche}</span></td>
                        <td><span class="stage-tag ${lead.stage}">${STAGE_LABELS[lead.stage] || lead.stage}</span></td>
                        <td style="font-size:0.72rem;line-height:1.5;">${contactHtml}</td>
                        <td>${escapeHtml(lead.country || lead.location || '') || '<span style="color:var(--text-tertiary)">—</span>'}</td>
                        <td>${formatDate(lead.created_at)}</td>
                        <td>
                            <div class="actions-cell" onclick="event.stopPropagation();">
                                <button class="action-btn" onclick="showOutreachForLead(${lead.id})" title="Generate outreach">✉️</button>
                                <button class="action-btn danger" onclick="deleteLead(${lead.id})" title="Delete">🗑️</button>
                            </div>
                        </td>
                    </tr>`;
                }).join('')}
            </tbody>
        </table>
    `;
}

function applyFilters() {
    state.filters.niche = document.getElementById('filter-niche').value;
    state.filters.stage = document.getElementById('filter-stage').value;
    state.filters.sort_by = document.getElementById('filter-sort').value;
    renderLeadTable();
}


// ── Lead Detail Modal ────────────────────────────────────────────────────────

async function showLeadDetail(leadId) {
    const lead = await api(`/leads/${leadId}`);
    const breakdown = await api(`/score/breakdown/${leadId}`);

    const signals = lead.signals || [];
    const maxScores = {
        niche_relevance: 18,
        has_email: 18,
        has_phone: 10,
        has_signals: 12,
        location_fit: 12,
        description_quality: 8,
        active_project: 8,
        decision_maker: 8,
        website_quality: 6,
    };

    showModal(`
        <div class="modal-header">
            <div class="modal-title">${escapeHtml(lead.company_name)}</div>
            <button class="modal-close" onclick="closeModal()">✕</button>
        </div>
        <div class="modal-body">
            <!-- Score + Tags -->
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
                <span class="score-badge ${getScoreClass(lead.icp_score)}" style="font-size:1.2rem;padding:6px 16px;">${lead.icp_score}</span>
                <span class="niche-tag ${lead.niche}">${NICHE_LABELS[lead.niche] || lead.niche}</span>
                <span class="stage-tag ${lead.stage}">${STAGE_LABELS[lead.stage] || lead.stage}</span>
            </div>

            <!-- Detail Fields -->
            <div class="detail-grid">
                <div class="detail-field">
                    <div class="detail-label">Website</div>
                    <div class="detail-value">${lead.website ? `<a href="${escapeHtml(lead.website)}" target="_blank">${escapeHtml(lead.domain || lead.website)}</a>` : '—'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">Contact Email</div>
                    <div class="detail-value">${lead.contact_email ? `<a href="mailto:${escapeHtml(lead.contact_email)}">${escapeHtml(lead.contact_email)}</a>` : '—'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">Phone Number</div>
                    <div class="detail-value">${lead.phone_number ? `<a href="tel:${escapeHtml(lead.phone_number)}">${escapeHtml(lead.phone_number)}</a>` : '—'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">Contact Name</div>
                    <div class="detail-value">${escapeHtml(lead.contact_name) || '—'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">Contact Role</div>
                    <div class="detail-value">${escapeHtml(lead.contact_role) || '—'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">Location</div>
                    <div class="detail-value">${escapeHtml(lead.location) || '—'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">Country</div>
                    <div class="detail-value">${escapeHtml(lead.country) || '—'}</div>
                </div>
                <div class="detail-field">
                    <div class="detail-label">Source</div>
                    <div class="detail-value">${escapeHtml(lead.source) || '—'}</div>
                </div>
            </div>

            <!-- Social Links -->
            ${(lead.linkedin_url || lead.instagram_url) ? `
            <div style="margin-top:12px;display:flex;gap:10px;">
                ${lead.linkedin_url ? `<a href="${escapeHtml(lead.linkedin_url)}" target="_blank" class="btn btn-secondary btn-sm" style="font-size:0.72rem;">🔗 LinkedIn</a>` : ''}
                ${lead.instagram_url ? `<a href="${escapeHtml(lead.instagram_url)}" target="_blank" class="btn btn-secondary btn-sm" style="font-size:0.72rem;">📸 Instagram</a>` : ''}
            </div>` : ''}

            <!-- Description -->
            <div style="margin-top:16px;">
                <div class="detail-label">Description</div>
                <div class="detail-value" style="font-size:0.78rem;line-height:1.6;color:var(--text-secondary);">${escapeHtml(lead.description) || 'No description available.'}</div>
            </div>

            <!-- Signals -->
            ${signals.length ? `
            <div style="margin-top:16px;">
                <div class="detail-label">Signals</div>
                <ul class="signals-list">
                    ${signals.map(s => `<li class="signal-chip">${escapeHtml(s)}</li>`).join('')}
                </ul>
            </div>` : ''}

            <!-- Score Breakdown -->
            <div style="margin-top:20px;">
                <div class="detail-label" style="margin-bottom:8px;">ICP Score Breakdown</div>
                <div class="score-breakdown">
                    ${Object.entries(breakdown.breakdown || {}).map(([key, val]) => `
                        <div class="score-row">
                            <span class="score-row-label">${key.replace(/_/g, ' ')}</span>
                            <div class="score-row-bar">
                                <div class="score-row-fill" style="width: ${(val / (maxScores[key] || 20)) * 100}%"></div>
                            </div>
                            <span class="score-row-value">${val}/${maxScores[key] || '?'}</span>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Stage Update -->
            <div style="margin-top:20px;">
                <div class="detail-label" style="margin-bottom:8px;">Pipeline Stage</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                    ${Object.entries(STAGE_LABELS).map(([key, label]) => `
                        <button class="btn ${lead.stage === key ? 'btn-primary' : 'btn-secondary'} btn-sm"
                            onclick="updateStage(${lead.id}, '${key}')">
                            ${label}
                        </button>
                    `).join('')}
                </div>
            </div>

            <!-- Notes -->
            <div style="margin-top:20px;">
                <div class="detail-label">Notes</div>
                <textarea class="form-input form-textarea" id="lead-notes-${lead.id}"
                    placeholder="Add notes about this lead...">${escapeHtml(lead.notes || '')}</textarea>
                <button class="btn btn-secondary btn-sm" style="margin-top:8px;"
                    onclick="saveNotes(${lead.id})">Save Notes</button>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-danger btn-sm" onclick="deleteLead(${lead.id}); closeModal();">Delete</button>
            <button class="btn btn-secondary" onclick="showOutreachForLead(${lead.id}); closeModal();">✉️ Generate Outreach</button>
            <button class="btn btn-primary" onclick="closeModal()">Done</button>
        </div>
    `);
}

async function updateStage(leadId, newStage) {
    await api(`/leads/${leadId}/stage`, { method: 'PUT', body: { stage: newStage } });
    showToast(`Moved to ${STAGE_LABELS[newStage]}`);
    closeModal();
    if (state.currentView === 'leads') renderLeadTable();
    if (state.currentView === 'pipeline') renderPipeline();
    if (state.currentView === 'dashboard') renderDashboard();
}

async function saveNotes(leadId) {
    const notes = document.getElementById(`lead-notes-${leadId}`).value;
    await api(`/leads/${leadId}`, { method: 'PUT', body: { notes } });
    showToast('Notes saved');
}

async function deleteLead(leadId) {
    if (!confirm('Delete this lead?')) return;
    await api(`/leads/${leadId}`, { method: 'DELETE' });
    showToast('Lead deleted', 'info');
    if (state.currentView === 'leads') renderLeadTable();
    if (state.currentView === 'pipeline') renderPipeline();
    if (state.currentView === 'dashboard') renderDashboard();
}


// ── Add Lead Modal ───────────────────────────────────────────────────────────

function showAddLeadModal() {
    showModal(`
        <div class="modal-header">
            <div class="modal-title">Add New Lead</div>
            <button class="modal-close" onclick="closeModal()">✕</button>
        </div>
        <div class="modal-body">
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Company Name *</label>
                    <input type="text" class="form-input" id="new-company-name" placeholder="Acme Corp">
                </div>
                <div class="form-group">
                    <label class="form-label">Website</label>
                    <input type="url" class="form-input" id="new-website" placeholder="https://acme.com">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Contact Name</label>
                    <input type="text" class="form-input" id="new-contact-name" placeholder="John Doe">
                </div>
                <div class="form-group">
                    <label class="form-label">Contact Email</label>
                    <input type="email" class="form-input" id="new-contact-email" placeholder="john@acme.com">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Contact Role</label>
                    <input type="text" class="form-input" id="new-contact-role" placeholder="Marketing Head">
                </div>
                <div class="form-group">
                    <label class="form-label">Phone Number</label>
                    <input type="tel" class="form-input" id="new-phone-number" placeholder="+1 555 123 4567">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Niche</label>
                    <select class="form-input" id="new-niche">
                        ${Object.entries(NICHE_LABELS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Location</label>
                <input type="text" class="form-input" id="new-location" placeholder="Mumbai, India">
            </div>
            <div class="form-group">
                <label class="form-label">Description / Notes</label>
                <textarea class="form-input form-textarea" id="new-description" placeholder="What does this company do?"></textarea>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="submitNewLead()">Add Lead</button>
        </div>
    `);
}

async function submitNewLead() {
    const data = {
        company_name: document.getElementById('new-company-name').value.trim(),
        website: document.getElementById('new-website').value.trim(),
        contact_name: document.getElementById('new-contact-name').value.trim(),
        contact_email: document.getElementById('new-contact-email').value.trim(),
        contact_role: document.getElementById('new-contact-role').value.trim(),
        phone_number: document.getElementById('new-phone-number').value.trim(),
        niche: document.getElementById('new-niche').value,
        location: document.getElementById('new-location').value.trim(),
        description: document.getElementById('new-description').value.trim(),
    };

    if (!data.company_name) {
        showToast('Company name is required', 'error');
        return;
    }

    // Extract domain from website
    if (data.website) {
        try {
            const url = new URL(data.website);
            data.domain = url.hostname.replace('www.', '');
        } catch (e) {
            data.domain = data.website;
        }
    }

    const result = await api('/leads', { method: 'POST', body: data });
    if (result.error) {
        showToast(result.error, 'error');
    } else {
        showToast(`Added ${data.company_name} (ICP: ${result.icp_score})`);
        closeModal();
        if (state.currentView === 'leads') renderLeadTable();
        if (state.currentView === 'dashboard') renderDashboard();
    }
}


// ═══════════════════════════════════════════════════════════════════════════════
// PIPELINE VIEW
// ═══════════════════════════════════════════════════════════════════════════════

async function renderPipeline() {
    const content = document.getElementById('content-area');
    content.innerHTML = '<div class="loading-state"><div class="spinner"></div> Loading pipeline...</div>';

    const pipeline = await api('/pipeline');
    state.pipeline = pipeline;

    const stages = ['research', 'contacted', 'replied', 'in_discussion', 'closed'];

    content.innerHTML = `
        <div class="pipeline-board">
            ${stages.map(stage => `
                <div class="pipeline-column" id="col-${stage}"
                    ondragover="handleDragOver(event)" ondrop="handleDrop(event, '${stage}')"
                    ondragleave="handleDragLeave(event)">
                    <div class="pipeline-column-header">
                        <span class="pipeline-column-title">${STAGE_LABELS[stage]}</span>
                        <span class="pipeline-column-count">${(pipeline[stage] || []).length}</span>
                    </div>
                    <div class="pipeline-column-body">
                        ${(pipeline[stage] || []).map(lead => `
                            <div class="pipeline-card" draggable="true"
                                ondragstart="handleDragStart(event, ${lead.id})"
                                onclick="showLeadDetail(${lead.id})">
                                <div class="pipeline-card-company">${escapeHtml(lead.company_name)}</div>
                                <div class="pipeline-card-meta">
                                    <span class="niche-tag pipeline-card-niche ${lead.niche}">${NICHE_LABELS[lead.niche] || lead.niche}</span>
                                    <span class="score-badge ${getScoreClass(lead.icp_score)}">${lead.icp_score}</span>
                                </div>
                            </div>
                        `).join('')}
                        ${(pipeline[stage] || []).length === 0 ? `
                            <div style="text-align:center;padding:20px;color:var(--text-tertiary);font-size:0.75rem;">
                                Drop leads here
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}


// ── Drag & Drop ──────────────────────────────────────────────────────────────

let draggedLeadId = null;

function handleDragStart(event, leadId) {
    draggedLeadId = leadId;
    event.dataTransfer.effectAllowed = 'move';
    event.target.style.opacity = '0.5';
}

function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    const col = event.currentTarget;
    col.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

async function handleDrop(event, newStage) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');

    if (draggedLeadId) {
        await api(`/leads/${draggedLeadId}/stage`, { method: 'PUT', body: { stage: newStage } });
        showToast(`Moved to ${STAGE_LABELS[newStage]}`);
        renderPipeline();
        draggedLeadId = null;
    }
}


// ═══════════════════════════════════════════════════════════════════════════════
// OUTREACH VIEW
// ═══════════════════════════════════════════════════════════════════════════════

async function renderOutreach() {
    const content = document.getElementById('content-area');
    const leads = await api('/leads?sort_by=icp_score&order=DESC&limit=100');
    state.leads = leads;

    if (!leads.length) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✉️</div>
                <h3>No leads to compose outreach for</h3>
                <p>Generate or add some leads first, then come here to draft personalized outreach.</p>
                <button class="btn btn-primary btn-lg" onclick="showGenerateView()">⚡ Generate Leads First</button>
            </div>
        `;
        return;
    }

    content.innerHTML = `
        <div class="outreach-layout">
            <div class="outreach-sidebar">
                <div class="outreach-sidebar-header">Select Lead</div>
                <div class="outreach-lead-list">
                    ${leads.map((l, i) => `
                        <div class="outreach-lead-item ${i === 0 ? 'active' : ''}"
                            data-lead-id="${l.id}" onclick="selectOutreachLead(${l.id}, this)">
                            <div class="outreach-lead-item-name">${escapeHtml(l.company_name)}</div>
                            <div class="outreach-lead-item-meta">
                                <span class="score-badge ${getScoreClass(l.icp_score)}" style="font-size:0.6rem;padding:1px 5px;">${l.icp_score}</span>
                                ${NICHE_LABELS[l.niche] || l.niche}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="outreach-editor">
                <div class="outreach-editor-header">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <select class="filter-select" id="outreach-channel" onchange="generateCurrentOutreach()">
                            <option value="email">📧 Email</option>
                            <option value="linkedin">💼 LinkedIn DM</option>
                        </select>
                        <select class="filter-select" id="outreach-followup">
                            <option value="">First Touch</option>
                            <option value="day4">Follow-up (Day 4)</option>
                            <option value="day10">Follow-up (Day 10)</option>
                        </select>
                    </div>
                    <div>
                        <button class="btn btn-secondary btn-sm" onclick="generateCurrentOutreach()">🔄 Regenerate</button>
                        <button class="btn btn-primary btn-sm" onclick="copyOutreach()">📋 Copy</button>
                    </div>
                </div>
                <div class="outreach-editor-body" id="outreach-body">
                    <div class="outreach-empty">
                        <div class="outreach-empty-icon">✉️</div>
                        <p>Select a lead and click generate to create a personalized outreach.</p>
                    </div>
                </div>
                <div class="outreach-controls">
                    <span class="word-count" id="outreach-word-count"></span>
                    <div style="display:flex;gap:6px;">
                        <button class="btn btn-ghost btn-sm" onclick="generateCurrentOutreach()">Generate Outreach</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Auto-select first lead
    if (leads.length > 0) {
        state.selectedLead = leads[0];
        generateCurrentOutreach();
    }
}

function selectOutreachLead(leadId, el) {
    document.querySelectorAll('.outreach-lead-item').forEach(item => item.classList.remove('active'));
    el.classList.add('active');

    state.selectedLead = state.leads.find(l => l.id === leadId);
    generateCurrentOutreach();
}

async function showOutreachForLead(leadId) {
    navigate('outreach');
    // Wait for render, then select the lead
    setTimeout(() => {
        const el = document.querySelector(`.outreach-lead-item[data-lead-id="${leadId}"]`);
        if (el) {
            selectOutreachLead(leadId, el);
        }
    }, 500);
}

async function generateCurrentOutreach() {
    if (!state.selectedLead) return;

    const body = document.getElementById('outreach-body');
    body.innerHTML = '<div class="loading-state"><div class="spinner"></div> Generating outreach...</div>';

    const channel = document.getElementById('outreach-channel').value;
    const followup = document.getElementById('outreach-followup').value;

    let result;

    if (followup) {
        result = await api('/outreach/followup', {
            method: 'POST',
            body: {
                lead_id: state.selectedLead.id,
                followup_type: followup,
            },
        });
    } else {
        result = await api('/outreach/generate', {
            method: 'POST',
            body: {
                lead_id: state.selectedLead.id,
                channel: channel,
            },
        });
    }

    const outreach = result.outreach || '';
    const lines = outreach.split('\n');
    let html = '';

    if (lines[0] && lines[0].startsWith('Subject:')) {
        html = `<div class="subject-line">${escapeHtml(lines[0])}</div>`;
        html += escapeHtml(lines.slice(2).join('\n'));
    } else {
        html = escapeHtml(outreach);
    }

    body.innerHTML = `<div class="outreach-preview">${html}</div>`;

    // Word count
    const wordCount = outreach.split(/\s+/).filter(Boolean).length;
    const wc = document.getElementById('outreach-word-count');
    if (wc) {
        wc.textContent = `${wordCount} words`;
        wc.style.color = wordCount > 200 ? 'var(--pink)' : 'var(--text-tertiary)';
    }
}

function copyOutreach() {
    const preview = document.querySelector('.outreach-preview');
    if (preview) {
        navigator.clipboard.writeText(preview.textContent).then(() => {
            showToast('Outreach copied to clipboard!');
        });
    }
}


// ═══════════════════════════════════════════════════════════════════════════════
// GENERATE VIEW
// ═══════════════════════════════════════════════════════════════════════════════

function renderGenerate() {
    const content = document.getElementById('content-area');

    content.innerHTML = `
        <div class="generate-container">
            <div class="generate-hero">
                <h2>Generate <span class="editorial">Leads</span></h2>
                <p>Select a niche and let the engine autonomously discover companies that match AtmonFX's ideal client profile.</p>
            </div>

            <div class="niche-grid">
                ${Object.entries(NICHE_LABELS).map(([key, label]) => `
                    <div class="niche-card ${state.selectedNiche === key ? 'selected' : ''}"
                        onclick="selectNiche('${key}', this)" id="niche-card-${key}">
                        <div class="niche-card-icon">${NICHE_ICONS[key]}</div>
                        <div class="niche-card-title">${label}</div>
                        <div class="niche-card-desc">${getNicheDescription(key)}</div>
                    </div>
                `).join('')}
            </div>

            <div class="generate-actions">
                <button class="btn btn-primary btn-lg" id="btn-generate" onclick="startGeneration()">
                    ⚡ Start Generating Leads
                </button>
            </div>

            <div class="generate-progress" id="generate-progress" style="display:none;">
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progress-bar"></div>
                </div>
                <div class="progress-message" id="progress-message">Initializing...</div>
            </div>
        </div>
    `;
}

function getNicheDescription(niche) {
    const descriptions = {
        'brand_cgi': 'D2C brands, FMCG, consumer goods, lifestyle',
        'ott_film': 'Production houses, OTT platforms, films',
        'archviz': 'Architecture firms, real estate developers',
        'gaming': 'Indie studios, mobile games, game art',
        'product_viz': 'E-commerce, manufacturers, packaging',
    };
    return descriptions[niche] || '';
}

function selectNiche(niche, el) {
    state.selectedNiche = niche;
    document.querySelectorAll('.niche-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
}

async function startGeneration() {
    const btn = document.getElementById('btn-generate');
    const progress = document.getElementById('generate-progress');

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Generating...';
    progress.style.display = 'block';

    // Show indicator in sidebar
    const indicator = document.getElementById('generation-indicator');
    indicator.style.display = 'flex';

    state.generating = true;

    // Start generation
    await api('/generate', {
        method: 'POST',
        body: {
            niche: state.selectedNiche,
            max_queries: 6,
            results_per_query: 12,
        },
    });

    // Poll for status
    pollGenerationStatus();
}

function pollGenerationStatus() {
    if (state.generationPollTimer) clearInterval(state.generationPollTimer);

    state.generationPollTimer = setInterval(async () => {
        const status = await api('/generate/status');

        const bar = document.getElementById('progress-bar');
        const msg = document.getElementById('progress-message');

        if (bar) bar.style.width = `${status.progress}%`;
        if (msg) msg.textContent = status.message || 'Processing...';

        if (!status.running) {
            clearInterval(state.generationPollTimer);
            state.generating = false;

            // Hide indicator
            const indicator = document.getElementById('generation-indicator');
            if (indicator) indicator.style.display = 'none';

            // Update button
            const btn = document.getElementById('btn-generate');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '⚡ Start Generating Leads';
            }

            if (status.results_count > 0) {
                showToast(`🎉 Generated ${status.results_count} new leads!`);

                // Show option to view leads
                const progress = document.getElementById('generate-progress');
                if (progress) {
                    progress.innerHTML += `
                        <div style="margin-top:20px;display:flex;gap:10px;justify-content:center;">
                            <button class="btn btn-primary" onclick="navigate('leads')">View Leads</button>
                            <button class="btn btn-secondary" onclick="navigate('pipeline')">View Pipeline</button>
                        </div>
                    `;
                }
            } else if (status.message && status.message.includes('Error')) {
                showToast(status.message, 'error');
            } else {
                showToast('Generation complete. No new leads found (duplicates filtered).', 'info');
            }
        }
    }, 1500);
}


// ── Utilities ────────────────────────────────────────────────────────────────

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
