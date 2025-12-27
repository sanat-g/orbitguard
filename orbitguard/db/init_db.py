#Setup that turns orbitguard.db into a real database with tables

from orbitguard.db.database import engine
#Base holds ORM table definitions (scan jobs, approach events, risk events)
from orbitguard.db.models import Base

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database tables created.")
