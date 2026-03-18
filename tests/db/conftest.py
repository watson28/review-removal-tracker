import subprocess
import time

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

CONTAINER_NAME = "rrt-test-postgres"
PG_PORT = 15432
PG_USER = "rrt"
PG_PASSWORD = "rrt"
PG_DB = "rrt_test"
DATABASE_URL = f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DB}"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.fixture(scope="session")
def pg_engine():
    _run([
        "podman", "run", "--rm", "-d",
        "--name", CONTAINER_NAME,
        "-e", f"POSTGRES_USER={PG_USER}",
        "-e", f"POSTGRES_PASSWORD={PG_PASSWORD}",
        "-e", f"POSTGRES_DB={PG_DB}",
        "-p", f"{PG_PORT}:5432",
        "docker.io/library/postgres:16",
    ])

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception:
            time.sleep(0.5)
    else:
        raise RuntimeError("PostgreSQL container did not become ready in time")

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")

    yield engine

    engine.dispose()
    _run(["podman", "stop", CONTAINER_NAME])


@pytest.fixture
def conn(pg_engine):
    with pg_engine.connect() as connection:
        connection.execute(text("BEGIN"))
        yield connection
        connection.rollback()
