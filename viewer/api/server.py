import os
import sys
from pathlib import Path
from flask import Flask, g
import psycopg2
from dotenv import load_dotenv

# Ensure viewer/ is on sys.path so `from api.routes import ...` resolves
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def get_db() -> psycopg2.extensions.connection:
    if "db" not in g:
        g.db = psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )
    return g.db


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates")

    @app.before_request
    def open_db() -> None:
        if "db" not in g:
            g.db = psycopg2.connect(
                host=os.environ["DB_HOST"],
                port=os.environ.get("DB_PORT", "5432"),
                dbname=os.environ["DB_NAME"],
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASSWORD"],
            )

    @app.teardown_appcontext
    def close_db(e: object = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    from api.routes import books_bp

    app.register_blueprint(books_bp)
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
