from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
import urllib.parse

# Carrega variáveis do .env
load_dotenv()

# Faz URL-encoding da senha para evitar problemas com caracteres especiais
password = urllib.parse.quote_plus(os.getenv('DB_PASSWORD', '1234@abcd'))

# Monta a URL de conexão
DATABASE_URL = (
    f"mysql+mysqlconnector://{os.getenv('DB_USER', 'rm1')}:"
    f"{password}@{os.getenv('DB_HOST', 'localhost')}:3306/"
    f"{os.getenv('DB_NAME', 'chamados_db')}"
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
