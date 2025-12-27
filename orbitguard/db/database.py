'''
This file creates: 
-- a single engine (the connection to sqlite file)
-- a sessionlocal factory (so api and worker can talk to db)
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_URL = "sqlite:///./orbitguard.db" 

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
