from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

load_dotenv()

# =========================
# FIX PYTHON PATH (SAFE)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.append(PROJECT_ROOT)

# =========================
# ALEMBIC CONFIG
# =========================
config = context.config

# =========================
# SAFE DATABASE URL
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL is not set")

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# =========================
# LOGGING
# =========================
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# =========================
# IMPORT MODELS (IMPORTANT)
# =========================
from database.database import Base
import database.models

target_metadata = Base.metadata


# =========================
# OFFLINE MODE
# =========================
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True  # 🔥 NEW
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================
# ONLINE MODE
# =========================
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,  # 🔥 NEW
            render_as_batch=True  # 🔥 FIX SQLite migration issue
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()