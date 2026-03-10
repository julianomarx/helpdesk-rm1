# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

# Routers
from routes import users, tickets, comments, auth, hotels, teams, categories, subcategories, ticket_logs, attachments

from database import Base, engine

# Cria tabelas do banco
Base.metadata.create_all(bind=engine)

# Inicializa app
app = FastAPI(
    title="Helpdesk Portal",
    version="1.0.0",
    root_path="/api"
)

# --------- FIX SWAGGER OPENAPI 3.1 -> 3.0.3 ---------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Helpdesk Portal",
        version="1.0.0",
        routes=app.routes,
        servers=[{"url": "/api"}]
    )

    # força versão compatível com Swagger UI
    openapi_schema["openapi"] = "3.0.3"

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
# ----------------------------------------------------

# CORS - liberando para Swagger externo (use com cuidado em produção)
origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 para Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Inclui routers
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

# Rota root
@app.get("/")
def root():
    return {"message": "Helpdesk API Online"}

# Rota de exemplo protegida (Swagger test)
@app.get("/secure-route")
def secure_route(token: str = Depends(oauth2_scheme)):
    return {"token_received": token}
