import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from passlib.context import CryptContext

from models import User as UserModel, UserHotel as UserHotelModel
from schemas import User, UserUpdate, UserCreate, UserHotelsUpdate, UserOut, UserTeamsUpdate, UserListOut
from models import RoleEnum
from database import get_db
from auth_utils import get_current_user

from services.user_service import create_user_service, update_user_hotels_service, list_users_service, get_user_service, update_user_service, delete_user_service, update_user_teams_service
from services.authorization import ensure_admin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/", response_model=User)
def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    created_user = create_user_service(user, db, current_user)
    
    db.commit()
    db.refresh(created_user)
        
    return created_user
    
@router.get("/", response_model=UserListOut)
def list_users(

    page: int = Query(
        default=1,
        ge=1
    ),

    page_size: int = Query(
        default=5,
        ge=1,
        le=100
    ),

    hotel_id: int | None = Query(default=None),
    role: RoleEnum | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    return list_users_service(
        page=page,
        page_size=page_size,
        hotel_id=hotel_id, 
        role=role, 
        search=search,
        db=db,
        current_user=current_user
    )
    
@router.get("/mentionable")
def get_mentionable_users(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    if current_user.role not in [RoleEnum.admin, RoleEnum.agent]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    users = (
        db.query(UserModel)
        .filter(UserModel.role.in_([RoleEnum.admin, RoleEnum.agent]))
        .order_by(UserModel.name)
        .all()
    )
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    
    user = get_user_service(current_user, user_id, db)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "hotels": [
            {
                "id": uh.hotel.id,
                "code": uh.hotel.code,
                "name": uh.hotel.name
            }
            for uh in user.hotels
        ],
        "teams": [
            {
                "id": ut.team.id,
                "name": ut.team.name
            }
            for ut in user.teams
        ]
    }

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int, 
    user_update: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    user = update_user_service(user_id, current_user, user_update, db)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: UserModel = Depends(ensure_admin)):
    
    
    delete_user_service(user_id, current_user, db)
    
    return { "message": f"Usuário {user_id} - foi deletado com sucesso." }

@router.put("/{user_id}/hotels")
def update_user_hotels(
    user_id: int,
    hotels_update: UserHotelsUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)):
    
    user = update_user_hotels_service(user_id, hotels_update, current_user, db)
    
    db.commit()

    return {"message": "ok"}

AVATAR_DIR = "uploads/avatars"
ALLOWED_AVATAR_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
ALLOWED_AVATAR_EXTS  = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(400, "Arquivo vazio não permitido")
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(413, f"Imagem muito grande. Máximo: {MAX_AVATAR_SIZE // 1024 // 1024} MB")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AVATAR_EXTS:
        raise HTTPException(400, f"Formato não suportado. Use: {', '.join(sorted(ALLOWED_AVATAR_EXTS))}")

    mime = (file.content_type or "").lower().split(";")[0].strip()
    if mime not in ALLOWED_AVATAR_MIMES:
        raise HTTPException(400, "Tipo de arquivo não é uma imagem válida")

    os.makedirs(AVATAR_DIR, exist_ok=True)

    # Apaga avatar antigo se existir
    if current_user.avatar_url:
        old_filename = current_user.avatar_url.split("/")[-1]
        old_path = os.path.join(AVATAR_DIR, old_filename)
        if os.path.isfile(old_path):
            os.remove(old_path)

    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(AVATAR_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    avatar_url = f"/api/users/avatar/{filename}"
    current_user.avatar_url = avatar_url
    db.commit()

    return {"avatar_url": avatar_url}


@router.get("/avatar/{filename}")
def serve_avatar(filename: str):
    if "/" in filename or ".." in filename or not filename:
        raise HTTPException(403)
    path = os.path.abspath(os.path.join(AVATAR_DIR, filename))
    root  = os.path.abspath(AVATAR_DIR)
    if not path.startswith(root + os.sep):
        raise HTTPException(403)
    if not os.path.isfile(path):
        raise HTTPException(404)
    return FileResponse(path)


@router.put("/{user_id}/teams")
def update_user_teams(
    user_id: int,
    teams_update: UserTeamsUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    user = update_user_teams_service(user_id, teams_update, db, current_user)

    db.commit()

    return {"message" : "ok"}

    