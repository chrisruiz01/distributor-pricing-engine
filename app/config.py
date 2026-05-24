import os
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def get_database_url() -> str:
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not all([db_host, db_port, db_name, db_user, db_password]):
        raise ValueError("Missing one or more required database environment variables.")
    
    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


def get_engine():
    return create_engine(get_database_url())