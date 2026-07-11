from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

NEW_COLUMNS = {
    "interaction_type": "VARCHAR(100) DEFAULT 'Meeting'",
    "time": "VARCHAR(20)",
    "attendees": "VARCHAR(500)",
    "topics_discussed": "TEXT",
    "materials_shared": "TEXT",
    "samples_distributed": "TEXT",
    "outcomes": "TEXT",
    "follow_up_actions": "TEXT",
    "ai_suggested_followups": "TEXT",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_db():
    inspector = inspect(engine)
    if "interactions" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("interactions")}
    with engine.begin() as conn:
        for col_name, col_type in NEW_COLUMNS.items():
            if col_name not in existing:
                conn.execute(
                    text(f"ALTER TABLE interactions ADD COLUMN {col_name} {col_type}")
                )


def init_db():
    from models import Interaction  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_db()
