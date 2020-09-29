import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    """Construct the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = bool(int(os.getenv("SQLALCHEMY_ECHO", '0')))

    db.init_app(app)

    with app.app_context():
        import routes  # Import routes
        db.create_all()  # Create sql tables for our data models

        return app