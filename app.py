from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

db = SQLAlchemy()

def create_app():
    load_dotenv()
    app = Flask(__name__, template_folder="templates")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Ensure models are registered
    from models import Product, StockMovement  # noqa: F401

    # Register blueprint
    from views import bp as main_bp
    app.register_blueprint(main_bp)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return redirect(url_for("main.products"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
