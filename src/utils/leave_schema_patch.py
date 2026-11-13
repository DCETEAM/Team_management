import logging
from sqlalchemy import inspect, text


def ensure_leave_request_mail_columns(db):
    """Add leave mail columns to existing DBs (create_all does not ALTER tables)."""
    try:
        insp = inspect(db.engine)
        if "leave_requests" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("leave_requests")}
        statements = []
        if "notify_to_admin_id" not in cols:
            statements.append(
                "ALTER TABLE leave_requests ADD COLUMN notify_to_admin_id INTEGER NULL"
            )
        if "notify_cc_admin_ids" not in cols:
            statements.append(
                "ALTER TABLE leave_requests ADD COLUMN notify_cc_admin_ids TEXT NULL"
            )
        for sql in statements:
            db.session.execute(text(sql))
        if statements:
            db.session.commit()
            logging.info("Patched leave_requests mail columns: %s", len(statements))
    except Exception as e:
        db.session.rollback()
        logging.warning("leave_requests schema patch skipped: %s", e)
