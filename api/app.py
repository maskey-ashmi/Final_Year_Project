import os
import sys

from flask import Flask, session, send_from_directory

# 1. FIX PATH RESOLUTION BEFORE ANY LOCAL IMPORTS
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR) if os.path.basename(CURRENT_DIR) == "api" else CURRENT_DIR

# Inject path arrays to ensure python finds subfolders inside /api
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(1, PROJECT_ROOT)

# Setup subfolder targets dynamically
sys.path.append(os.path.join(PROJECT_ROOT, "rf"))
sys.path.append(os.path.join(CURRENT_DIR, "rf"))

# Import Flask configuration mapping
from config import config_by_name
# Expose RandomForest and DecisionTree for pickle loading
import random_forest_from_scratch as _rf_mod
import __main__
__main__.RandomForest = _rf_mod.RandomForest
__main__.DecisionTree = _rf_mod.DecisionTree
__main__.Node = _rf_mod.Node

from database import bcrypt, init_extensions
from database import user_models, doctor_models  # noqa: F401
from database.doctor_models import Doctor
from database.user_models import User
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp
from routes.prediction_routes import prediction_bp
from routes.admin_routes import admin_bp


DEFAULT_DOCTORS = [
    {
        "name": "Dr. Maya Sharma",
        "specialization": "Dermatologist",
        "location": "Kathmandu Skin Center",
        "experience_years": 11,
        "rating": 4.9,
    },
    {
        "name": "Dr. Aarav Singh",
        "specialization": "Acne Specialist",
        "location": "City Care Clinic",
        "experience_years": 8,
        "rating": 4.8,
    },
    {
        "name": "Dr. Nisha Karki",
        "specialization": "Skin and Laser Specialist",
        "location": "Glow Derm Studio",
        "experience_years": 9,
        "rating": 4.7,
    },
]


def seed_default_doctors():
    """Seed default doctors if the database is configured.

    This function now safely handles the case where the DATABASE_URL is not set
    (e.g., during local development without a MySQL server). It attempts to
    query existing doctors and, on any RuntimeError, simply skips seeding.
    """
    try:
        existing = Doctor.all()
        if existing:
            return
        for doctor_data in DEFAULT_DOCTORS:
            Doctor.create(
                name=doctor_data.get("name"),
                specialization=doctor_data.get("specialization"),
                location=doctor_data.get("location"),
                experience_years=doctor_data.get("experience_years"),
                rating=doctor_data.get("rating"),
            )
    except RuntimeError:
        # Database not configured; skip seeding doctors.
        pass
    except Exception:
        pass


def seed_default_admin():
    """Seed a default admin user if possible.

    The function now guards against missing database configuration by wrapping
    all operations in a try/except block.
    """
    try:
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@skinsense.ai")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        existing_admin = User.get_by_email(admin_email)
        if existing_admin is not None:
            return
        User.create(
            name="SkinSense Admin",
            email=admin_email,
            password_hash=bcrypt.generate_password_hash(admin_password).decode("utf-8"),
            age=30,
            skin_type="combination",
            role="admin",
        )
    except RuntimeError:
        # Database not configured; skip admin seeding.
        pass
    except Exception:
        pass


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Enhanced session configuration
    app.config.update(
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=False,  # Set to False for HTTP in development
    )

    # 2. CRITICAL VERCEL FIX: Force write paths to system /tmp 
    if os.environ.get("VERCEL") == "1":
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"

    # Safely create folders without raising read-only workspace errors
    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    except Exception as e:
        print(f"Skipping storage folder creation for Vercel: {e}")

    # Init extensions and database
    init_extensions(app)

    with app.app_context():
        # Ensure DB config is available to helpers
        seed_default_doctors()
        seed_default_admin()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(admin_bp)

    # Serve uploaded images from the uploads/ folder (outside static/)
    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # Session management
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    return app


# CRITICAL FIX FOR VERCEL DEPLOYMENT:
# Instantiate the Flask instance globally at the root level of the file
# Vercel looks for this 'app' or 'application' variable directly when launching.
config_mode = os.environ.get("FLASK_CONFIG", "production")
app = create_app(config_mode)
application = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)
