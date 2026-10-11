from sqlalchemy import text

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine


def main() -> None:
    engine = create_db_engine(Settings())

    try:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT current_database(), current_user")).one()
            print(f"Database: {row[0]}")
            print(f"User: {row[1]}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
