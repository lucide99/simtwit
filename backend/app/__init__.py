"""SimTwit Backend - Flask App"""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env from project root
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file, override=True)


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from .api import simtwit_bp
    app.register_blueprint(simtwit_bp, url_prefix='/api')

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'SimTwit Backend'}

    return app
