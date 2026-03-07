from fastapi import FastAPI
from database import engine, Base
from routes import users, tickets, comments, auth, hotels, teams, categories, subcategories, ticket_logs, attachments # sua pasta routes
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles


# Cria todas as tabelas que ainda não existem 
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Helpdesk Portal")

origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # permite apenas essas origens
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    
)
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

#Serve os arquivos estáticos (Attachments)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "Helpdesk API Online"}