import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Faz URL-encoding da senha
password = urllib.parse.quote_plus(os.getenv('DB_PASSWORD', '1234@abcd'))

# Monta a URL de conexão corretamente
DATABASE_URL = f"mysql+mysqlconnector://rm1:{password}@147.15.86.148:3306/helpdesk"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base para modelos
Base = declarative_base()

# Função utilitária para pegar sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()