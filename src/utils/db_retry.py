import logging
from functools import wraps

from flask import jsonify
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from src import db


def ensure_db_connection():
    """Ensure database connection is alive, else reconnect."""
    try:
        db.session.execute(text("SELECT 1"))
    except OperationalError as e:
        if "MySQL server has gone away" in str(e) or "Lost connection" in str(e):
            db.session.rollback()
            db.engine.dispose()
            db.session.remove()
            logging.warning("Database connection lost, reconnected.")
        else:
            raise e


def with_db_reconnect(func):
    """Decorator to ensure DB connection before running any API route handler."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ensure_db_connection()
            return func(*args, **kwargs)
        except OperationalError as e:
            return (
                jsonify(
                    {
                        "success": 0,
                        "error": "Database connection error: " + str(e),
                    }
                ),
                500,
            )
        except Exception as e:
            return jsonify({"success": 0, "error": str(e)}), 500

    return wrapper
