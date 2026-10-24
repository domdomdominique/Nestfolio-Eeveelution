"""Add/backfill phone fingerprints without resetting existing database records."""
import sqlite3
from pathlib import Path

from app import create_app
from app.entity.db import db
from app.entity.encryption import decrypt, phone_digest


def upgrade_phone_hashes(connection):
    connection.execute("BEGIN IMMEDIATE")
    try:
        updates = {}
        for table in ("user_account", "designer_application"):
            rows = connection.execute(f"SELECT id, phone FROM {table}").fetchall()
            values = []
            seen = {}
            for record_id, encrypted_phone in rows:
                try:
                    phone = decrypt(encrypted_phone) if encrypted_phone else None
                except (ValueError, AttributeError):
                    raise RuntimeError(
                        f"Cannot read phone for {table} ID {record_id}. "
                        "Keep the original ENCRYPTION_KEY; do not reset the database."
                    ) from None
                digest = phone_digest(phone)
                if table == "user_account" and digest:
                    if digest in seen:
                        raise RuntimeError(
                            f"Accounts {seen[digest]} and {record_id} share a phone. "
                            "Resolve that duplicate before retrying. No records were deleted."
                        )
                    seen[digest] = record_id
                values.append((digest, record_id))
            updates[table] = values

        for table, values in updates.items():
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            if "phone_hash" not in columns:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN phone_hash VARCHAR(64)")
            connection.executemany(f"UPDATE {table} SET phone_hash=? WHERE id=?", values)

        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_user_account_phone_hash "
            "ON user_account(phone_hash)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_designer_application_phone_hash "
            "ON designer_application(phone_hash)"
        )
        connection.commit()
        return {table: len(values) for table, values in updates.items()}
    except Exception:
        connection.rollback()
        raise


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        path = Path(db.engine.url.database).resolve()
        with sqlite3.connect(path.as_uri() + "?mode=rw", uri=True) as connection:
            counts = upgrade_phone_hashes(connection)
        print("Database upgraded successfully:", path)
        print("Existing records preserved:", counts)
