from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from routes import (
    users, tickets, comments, auth, hotels, teams, categories, subcategories, ticket_logs, attachments
)

# Cria as tabelas que ainda não existem
Base.metadata.create_all(bind=engine)

# Desativa o docs padrão e cria rota custom
app = FastAPI(title="Helpdesk Portal", docs_url=None, redoc_url=None)

# CORS liberado para qualquer origem (só para o Swagger funcionar fora)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # aceita qualquer origem
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers da aplicação
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

# Serve arquivos estáticos (attachments)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve a documentação Swagger pública
from fastapi.openapi.docs import get_swagger_ui_html

@app.get("/docs", include_in_schema=False)
async def swagger_docs():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Helpdesk Docs")

@app.get("/")
def root():
    return {"message": "Helpdesk API Online"}