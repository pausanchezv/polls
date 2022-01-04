from collections.abc import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.settings import settings

engine = create_engine(settings.postgres_url, pool_recycle=3600, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class DBManager:
	@staticmethod
	@contextmanager
	def get_db() -> Generator[Session]:
		return get_db()


def get_db_with_context_manager() -> Generator[Session]:
	return DBManager().get_db()


def get_db() -> Generator[Session]:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
