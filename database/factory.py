from __future__ import annotations

from database.postgres import PostgresRepository
from database.sqlite import SQLiteRepository


def create_repository(database_url: str):
    if database_url.startswith(("postgresql://", "postgres://")):
        return PostgresRepository(database_url)
    if database_url.startswith("sqlite:///"):
        return SQLiteRepository(database_url.removeprefix("sqlite:///"))
    raise ValueError("DATABASE_URL must begin with postgresql://, postgres://, or sqlite:///")
