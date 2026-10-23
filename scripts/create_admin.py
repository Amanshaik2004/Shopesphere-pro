import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import SessionLocal
from app.db.init_db import init_db

if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
        print("Database initialized and Super Admin verified.")
    finally:
        db.close()
