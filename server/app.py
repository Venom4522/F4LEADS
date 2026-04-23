"""
F4Leads Server — Flask application with API routes and dashboard serving.
"""

import logging
import threading
from flask import Flask, jsonify, request, render_template, send_from_directory

from engine.database import (
    get_all_leads, get_lead, add_lead, update_lead, delete_lead,
    get_stats, get_leads_by_stage, add_outreach, get_outreach_history, log_search
)
from engine.scraper import LeadScraper
from engine.scorer import score_lead, get_score_breakdown, get_score_label
from engine.outreach import (
    generate_outreach, generate_followup, get_available_templates, get_template_preview
)

import os

logger = logging.getLogger(__name__)

# ─── APP FACTORY ──────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static'),
    )
    app.config['JSON_SORT_KEYS'] = False

    # Track generation status
    app.generation_status = {
        'running': False,
        'progress': 0,
        'message': '',
        'results_count': 0,
    }

    register_routes(app)
    return app


# ─── ROUTES ───────────────────────────────────────────────────────────────────

def register_routes(app):

    # ── Dashboard ────────────────────────────────────────────────────────

    @app.route('/')
    def index():
        return render_template('index.html')

    # ── API: Stats ───────────────────────────────────────────────────────

    @app.route('/api/stats')
    def api_stats():
        stats = get_stats()
        return jsonify(stats)

    # ── API: Leads CRUD ──────────────────────────────────────────────────

    @app.route('/api/leads')
    def api_leads():
        niche = request.args.get('niche', 'all')
        stage = request.args.get('stage', 'all')
        min_score = request.args.get('min_score', type=int)
        sort_by = request.args.get('sort_by', 'icp_score')
        order = request.args.get('order', 'DESC')
        limit = request.args.get('limit', 200, type=int)

        leads = get_all_leads(
            niche=niche, stage=stage, min_score=min_score,
            sort_by=sort_by, order=order, limit=limit
        )
        return jsonify(leads)

    @app.route('/api/leads', methods=['POST'])
    def api_add_lead():
        data = request.get_json()
        if not data or not data.get('company_name'):
            return jsonify({'error': 'company_name is required'}), 400

        # Auto-score the lead
        data['icp_score'] = score_lead(data)

        lead_id = add_lead(data)
        if lead_id is None:
            return jsonify({'error': 'Duplicate lead (same domain already exists)'}), 409

        lead = get_lead(lead_id)
        return jsonify(lead), 201

    @app.route('/api/leads/<int:lead_id>')
    def api_get_lead(lead_id):
        lead = get_lead(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        return jsonify(lead)

    @app.route('/api/leads/<int:lead_id>', methods=['PUT'])
    def api_update_lead(lead_id):
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Re-score if relevant fields changed
        score_fields = {'niche', 'contact_email', 'contact_role', 'phone_number', 'signals', 'location', 'country', 'description'}
        if any(field in data for field in score_fields):
            current = get_lead(lead_id)
            if current:
                merged = {**current, **data}
                data['icp_score'] = score_lead(merged)

        success = update_lead(lead_id, data)
        if not success:
            return jsonify({'error': 'No valid fields to update'}), 400

        lead = get_lead(lead_id)
        return jsonify(lead)

    @app.route('/api/leads/<int:lead_id>', methods=['DELETE'])
    def api_delete_lead(lead_id):
        delete_lead(lead_id)
        return jsonify({'success': True})

    @app.route('/api/leads/<int:lead_id>/stage', methods=['PUT'])
    def api_update_stage(lead_id):
        data = request.get_json()
        stage = data.get('stage')
        valid_stages = ['research', 'contacted', 'replied', 'in_discussion', 'closed']
        if stage not in valid_stages:
            return jsonify({'error': f'Invalid stage. Must be one of: {valid_stages}'}), 400

        update_lead(lead_id, {'stage': stage})
        lead = get_lead(lead_id)
        return jsonify(lead)

    # ── API: Pipeline ────────────────────────────────────────────────────

    @app.route('/api/pipeline')
    def api_pipeline():
        pipeline = get_leads_by_stage()
        return jsonify(pipeline)

    # ── API: Lead Generation ─────────────────────────────────────────────

    @app.route('/api/generate', methods=['POST'])
    def api_generate():
        """Trigger autonomous lead generation."""
        if app.generation_status['running']:
            return jsonify({'error': 'Generation already in progress'}), 409

        data = request.get_json() or {}
        niche = data.get('niche', 'brand_cgi')
        max_queries = data.get('max_queries', 6)
        results_per_query = data.get('results_per_query', 12)

        def run_generation():
            app.generation_status['running'] = True
            app.generation_status['progress'] = 0
            app.generation_status['message'] = 'Starting lead generation...'
            app.generation_status['results_count'] = 0

            try:
                scraper = LeadScraper()

                def progress_callback(message, progress):
                    app.generation_status['message'] = message
                    app.generation_status['progress'] = progress

                leads = scraper.generate_leads(
                    niche=niche,
                    max_queries=max_queries,
                    results_per_query=results_per_query,
                    progress_callback=progress_callback,
                )

                # Save leads to database
                saved_count = 0
                for lead in leads:
                    lead_id = add_lead(lead)
                    if lead_id is not None:
                        saved_count += 1

                app.generation_status['message'] = f'Done! Generated {saved_count} new leads.'
                app.generation_status['results_count'] = saved_count
                app.generation_status['progress'] = 100

                # Log the search
                log_search(f"Auto-generate: {niche}", niche, saved_count)

            except Exception as e:
                logger.error(f"Generation error: {e}")
                app.generation_status['message'] = f'Error: {str(e)}'
            finally:
                app.generation_status['running'] = False

        thread = threading.Thread(target=run_generation, daemon=True)
        thread.start()

        return jsonify({'status': 'started', 'niche': niche})

    @app.route('/api/generate/status')
    def api_generate_status():
        """Check lead generation progress."""
        return jsonify(app.generation_status)

    # ── API: Outreach ────────────────────────────────────────────────────

    @app.route('/api/outreach/generate', methods=['POST'])
    def api_generate_outreach():
        """Generate outreach for a specific lead."""
        data = request.get_json()
        lead_id = data.get('lead_id')
        channel = data.get('channel', 'email')
        template_type = data.get('template_type')

        if not lead_id:
            return jsonify({'error': 'lead_id is required'}), 400

        lead = get_lead(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404

        outreach = generate_outreach(lead, channel=channel, template_type=template_type)

        # Save draft to lead
        update_lead(lead_id, {'outreach_draft': outreach})

        # Log outreach
        add_outreach(lead_id, template_type or lead['niche'], channel, outreach)

        return jsonify({
            'outreach': outreach,
            'channel': channel,
            'lead_id': lead_id,
        })

    @app.route('/api/outreach/followup', methods=['POST'])
    def api_generate_followup():
        """Generate a follow-up for a lead."""
        data = request.get_json()
        lead_id = data.get('lead_id')
        followup_type = data.get('followup_type', 'day4')

        if not lead_id:
            return jsonify({'error': 'lead_id is required'}), 400

        lead = get_lead(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404

        followup = generate_followup(lead, followup_type=followup_type)
        add_outreach(lead_id, followup_type, 'email', followup)

        return jsonify({'outreach': followup, 'type': followup_type, 'lead_id': lead_id})

    @app.route('/api/outreach/history/<int:lead_id>')
    def api_outreach_history(lead_id):
        history = get_outreach_history(lead_id)
        return jsonify(history)

    @app.route('/api/outreach/templates')
    def api_templates():
        return jsonify(get_available_templates())

    @app.route('/api/outreach/preview')
    def api_template_preview():
        niche = request.args.get('niche', 'brand_cgi')
        channel = request.args.get('channel', 'email')
        return jsonify({'preview': get_template_preview(niche, channel)})

    # ── API: Score ───────────────────────────────────────────────────────

    @app.route('/api/score/breakdown/<int:lead_id>')
    def api_score_breakdown(lead_id):
        lead = get_lead(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404

        breakdown = get_score_breakdown(lead)
        label = get_score_label(lead['icp_score'])

        return jsonify({
            'score': lead['icp_score'],
            'label': label,
            'breakdown': breakdown,
        })

    @app.route('/api/leads/<int:lead_id>/rescore', methods=['POST'])
    def api_rescore_lead(lead_id):
        lead = get_lead(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404

        new_score = score_lead(lead)
        update_lead(lead_id, {'icp_score': new_score})

        return jsonify({'score': new_score, 'label': get_score_label(new_score)})
