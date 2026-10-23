"""Validação de configuração sem conexão com o banco nem exposição de segredos."""
from dataclasses import dataclass

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True, repr=False)
class Settings:
    database_url: str
    admin_password: str


def validate_settings(values):
    try:
        raw_url = values.get("DB_URL")
        password = values.get("SENHA_ADM")
        if not isinstance(password, str) or not password.strip():
            raise ValueError
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise ValueError
        raw_url = raw_url.strip()
        if raw_url.startswith("postgres://"):
            raw_url = "postgresql://" + raw_url[len("postgres://"):]
        url = make_url(raw_url)
        if url.drivername not in ("postgresql", "postgresql+psycopg2"):
            raise ValueError
        if not all((url.host, url.database, url.username, url.password)):
            raise ValueError
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError
    except (ValueError, TypeError, KeyError, ArgumentError):
        raise ConfigurationError("Defina DB_URL PostgreSQL válida e SENHA_ADM não vazia.") from None
    return Settings(raw_url, password)
