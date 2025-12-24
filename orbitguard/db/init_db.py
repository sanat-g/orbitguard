# orbitguard/db/init_db.py
from orbitguard.db.database import engine
from orbitguard.db.models import Base

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("✅ Database tables created.")
