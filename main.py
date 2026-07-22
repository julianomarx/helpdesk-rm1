import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

from routes import users, tickets, comments, auth, hotels, teams, categories, subcategories, ticket_logs, attachments, dashboard, sla, reports, notifications, todos, mural, qualitor, admin_health

from config import validate_env, UPLOADS_DIR, AVATAR_DIR, TICKETS_DIR

validate_env()

# Garante que os diretórios de upload existem antes de montar o StaticFiles
os.makedirs(AVATAR_DIR,  exist_ok=True)
os.makedirs(TICKETS_DIR, exist_ok=True)

from database import Base, engine

#Só cria as tabelas se estiver em embiente DEV, em PRDO somente via MIGRATION
if os.getenv("ENV") == "dev":
    Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pré-aquece o pool de conexões do banco para evitar lentidão após reinicialização.
    # Abre pool_size conexões simultâneas antes de aceitar requests.
    from database import engine
    from sqlalchemy import text
    from concurrent.futures import ThreadPoolExecutor
    import asyncio

    def _ping():
        try:
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
        except Exception:
            pass  # warmup é best-effort; falha não impede o startup

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=5) as ex:
        await asyncio.gather(*[loop.run_in_executor(ex, _ping) for _ in range(5)])

    yield

# Inicializa app
app = FastAPI(
    title="Helpdesk Portal",
    version="1.0.0",
    root_path="/api",
    redirect_slashes=False,
    lifespan=lifespan,
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Helpdesk Portal",
        version="1.0.0",
        routes=app.routes,
        servers=[{"url": "/api"}]
    )

    openapi_schema["openapi"] = "3.0.3"

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
app.include_router(dashboard.router)
app.include_router(sla.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(todos.router)
app.include_router(mural.router)
app.include_router(qualitor.router)
app.include_router(admin_health.router)

# Serve arquivos estáticos — aponta para diretório externo ao repositório
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Rota root
@app.get("/")
def root():
    return {"message": "Helpdesk API Online"}

# Rota de exemplo protegida (Swagger test)
@app.get("/secure-route")
def secure_route(token: str = Depends(oauth2_scheme)):
    return {"token_received": token}
