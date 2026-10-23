"""Validação anterior ao deploy; nunca instala pacotes ou altera o banco."""
import argparse
import importlib
from importlib.metadata import version
from pathlib import Path
import sys
import tomllib


PACKAGES = {
    "streamlit": "streamlit", "pandas": "pandas", "plotly.express": "plotly",
    "sqlalchemy": "SQLAlchemy", "psycopg2": "psycopg2-binary",
    "PIL.Image": "pillow", "folium": "folium",
    "streamlit_folium": "streamlit-folium", "fpdf.enums": "fpdf2",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secrets", type=Path,
                        default=Path(".streamlit/secrets.toml"))
    parser.add_argument("--check-db", action="store_true",
                        help="Executa apenas SELECT 1 no banco configurado")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        print("Use Python 3.12, a mesma versão configurada no deploy.")
        return 1
    failed = []
    for module, distribution in PACKAGES.items():
        try:
            importlib.import_module(module)
            print(f"OK: {distribution}=={version(distribution)}")
        except Exception:
            failed.append(distribution)
    if failed:
        print("Dependências ausentes ou incompatíveis: " + ", ".join(failed))
        print("Execute: python -m pip install -r requirements.txt")
        return 1
    from configuration import ConfigurationError, validate_settings
    try:
        with args.secrets.open("rb") as file:
            settings = validate_settings(tomllib.load(file))
    except (OSError, tomllib.TOMLDecodeError, ConfigurationError):
        print("Secrets ausentes ou inválidos. Consulte .streamlit/secrets.toml.example.")
        return 1
    print("OK: configuração válida (valores omitidos).")
    if args.check_db:
        from sqlalchemy import create_engine, text
        engine = None
        try:
            engine = create_engine(settings.database_url, pool_pre_ping=True,
                                   connect_args={"connect_timeout": 10})
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            print("Falha na conexão. Verifique DB_URL, SSL, rede e permissões.")
            return 1
        finally:
            if engine is not None:
                engine.dispose()
        print("OK: conexão com o banco (SELECT 1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
