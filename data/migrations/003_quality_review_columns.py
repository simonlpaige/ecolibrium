"""
Migration 003: add explicit quality and review columns.
"""

import os
import sqlite3

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.dirname(_THIS_DIR)
DB_PATH = os.path.join(_DATA_DIR, "ecolibrium_directory.db")


def add_column(cursor, name, sql_type):
    cursor.execute("PRAGMA table_info(organizations)")
    existing = {row[1] for row in cursor.fetchall()}
    if name in existing:
        return
    cursor.execute(f"ALTER TABLE organizations ADD COLUMN {name} {sql_type}")


def run():
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    add_column(c, "quality_tier", "TEXT")
    add_column(c, "review_status", "TEXT DEFAULT 'unreviewed'")
    add_column(c, "scored_pass", "INTEGER DEFAULT 0")
    db.commit()
    db.close()
    print("Added quality_tier, review_status, and scored_pass")


if __name__ == "__main__":
    run()
