from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


def _engine_args(database_url: str) -> tuple[str, dict]:
    """sqlalchemy-libsql exige el authToken de Turso vía connect_args, no como
    query param en la URL (a diferencia de lo que sugiere buena parte de la
    documentacion de terceros) - si va en la URL, el handshake websocket con
    Turso falla con 400 Invalid response status.
    """
    if database_url.startswith("sqlite:///"):
        return database_url, {"check_same_thread": False}

    if "+libsql" in database_url:
        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        auth_token = query.pop("authToken", [None])[0]
        clean_url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
        connect_args = {"auth_token": auth_token} if auth_token else {}
        return clean_url, connect_args

    return database_url, {}


_url, connect_args = _engine_args(settings.database_url)
engine = create_engine(_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
