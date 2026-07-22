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
#engine = create_engine(DATABASE_URL, echo=True)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=900,   # recicla antes do wait_timeout do MySQL (evita conexão morta silenciosa)
    pool_timeout=15,
    connect_args={"connection_timeout": 5},  # falha rápido se MySQL não responder
)


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
