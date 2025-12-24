from typing import Generator
from sqlalchemy.orm import Session
from orbitguard.db.database import SessionLocal

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        #yield lets fastapi borrow the session for the request, then always runs to close it.
        yield db
    finally:
        db.close()
