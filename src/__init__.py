import logging
from flask import Flask, current_app, send_from_directory, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from config import Config

# from src.middlewares.agent_check import restrict_user_agents

# Init db
db = SQLAlchemy()


def create_app():

    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s | %(levelname)s | %(message)s"
    )

    # Create app
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    cors_allow_headers = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "X-Client-Time",
        "X-Client-Local-Date",
    ]

    # Handling CORS
    CORS(
        app,
        resources={
            r"/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": cors_allow_headers,
                "expose_headers": ["Content-Type", "Authorization"],
            }
        },
        supports_credentials=True,
    )

    # Handle OPTIONS requests explicitly
    @app.before_request
    def handle_options_request():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = ", ".join(cors_allow_headers)
            return response

    # Middlewares
    # Agent check
    # restrict_user_agents(app)

    # Configuration
    try:
        app.config.from_object(Config)
        logging.info("Configuration Success")
    except Exception as e:
        logging.error(f"Configuration Failed, {e}")

    # Connect the db to app
    try:
        db.init_app(app)
        logging.info("DB Initialized Successfully.")
    except Exception as e:
        logging.error(f"DB Initialize Failed, {e}")

    # Init migration
    migrate = Migrate(app, db)
    logging.info("Migrate Initialized Successfully.")

    # Import routes
    try:

        @app.route("/api/v1/src/assets/<path:filename>")
        def serve_static(filename):
            return send_from_directory(
                current_app.config["SERVE_STATIC_FOLDER"], filename
            )

        from src.routes import init_routes

        init_routes(app)
        logging.info("Routes Initialized Successfully.")

    except Exception as e:
        logging.error(f"Routes Initialize Failed ,{e}")

    with app.app_context():
        db.create_all()

    @app.teardown_request
    def _teardown_db_session(exc):
        try:
            if exc is not None:
                db.session.rollback()
        except Exception:
            pass
        finally:
            db.session.remove()

    return app
