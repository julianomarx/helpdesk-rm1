from fastapi import FastAPI
from database import engine, Base
from routes import users, tickets, comments  # sua pasta routes

# Cria todas as tabelas que ainda não existem
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Helpdesk Portal")

# Inclui os routers
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(comments.router)

@app.get("/")
def root():
    return {"message": "Helpdesk API Online"}