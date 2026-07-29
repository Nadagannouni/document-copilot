from __future__ import annotations

from sqlalchemy.engine import make_url

from app.config import settings


def database_url() -> str:
    url = make_url(str(settings.database_url))
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)
