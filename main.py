from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles

# Importa seus routers
from routes import users, tickets, comments, auth, hotels, teams, categories, subcategories, ticket_logs, attachments

from database import Base, engine

# Cria as tabelas do banco, se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Helpdesk Portal")

# CORS - ajuste conforme seu front / domínio externo
origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "*",  # liberando todas origens para documentação funcionar fora (use com cuidado em produção)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define o esquema OAuth2 para Swagger (botão Authorize)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Inclui os routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(comments.router)
app.include_router(hotels.router)
app.include_router(teams.router)
app.include_router(categories.router)
app.include_router(subcategories.router)
app.include_router(ticket_logs.router)
app.include_router(attachments.router)

# Serve arquivos estáticos (ex: uploads)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Rota root simples
@app.get("/")
def root():
    return {"message": "Helpdesk API Online"}

# Exemplo de rota protegida usando o oauth2_scheme para Swagger funcionar direitinho
@app.get("/secure-route")
def secure_route(token: str = Depends(oauth2_scheme)):
    return {"token_received": token}