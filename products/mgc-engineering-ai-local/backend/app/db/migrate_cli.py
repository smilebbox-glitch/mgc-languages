"""One-shot schema migration command for least-privilege enterprise deployment."""
from app.db import models  # noqa: F401
from app.db.bootstrap import bootstrap_schema
from app.db.session import Base, engine


def main() -> None:
    bootstrap_schema(engine, Base.metadata)
    print("MGC schema migration complete")


if __name__ == "__main__":
    main()
