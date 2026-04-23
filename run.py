"""
F4Leads — Run the application.
"""

import logging
import webbrowser
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger('F4Leads')


def main():
    """Start the F4Leads server."""
    logger.info("=" * 60)
    logger.info("  F4Leads — AtmonFX Lead Generation Engine")
    logger.info("=" * 60)

    from server.app import create_app

    app = create_app()

    host = '127.0.0.1'
    port = 5000

    logger.info(f"  Starting server at http://{host}:{port}")
    logger.info(f"  Press Ctrl+C to stop")
    logger.info("=" * 60)

    # Open browser
    webbrowser.open(f'http://{host}:{port}')

    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
