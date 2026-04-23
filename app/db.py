from sqlmodel import Session, create_engine

from app.config import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session():
    with Session(get_engine()) as session:
        yield session
