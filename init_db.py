"""
Run this once before first use:

    python init_db.py

Creates the SQLite database (data/rfi_assistant.db) and, if it's empty,
seeds it with the 2 real sample RFIs + a handful of synthetic demo RFIs so
search / dashboard / draft-assistant all have something to work with
immediately.
"""
from core.database import init_db, get_session
from core.seed_data import seed_if_empty

if __name__ == "__main__":
    init_db()
    with get_session() as session:
        added = seed_if_empty(session)
    if added:
        print(f"Database initialized and seeded with {added} sample RFIs.")
    else:
        print("Database already initialized (not re-seeded, it already has data).")
