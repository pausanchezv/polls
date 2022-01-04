from sqlalchemy import Column, Integer, String
from app.db.db import Base


class Counter(Base):
    __tablename__ = "counters"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, nullable=False)
    count = Column(Integer, nullable=False, default=0)
