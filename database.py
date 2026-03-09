from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
import urllib.parse

# Carrega variáveis do .env
load_dotenv()

# Faz URL-encoding da senha para evitar problemas com caracteres especiais
password = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))

DATABASE_URL = (
    f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{password}"
    f"@{os.getenv('DB_HOST')}:3306/{os.getenv('DB_NAME')}"
)

# Cria engine e sessão
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
