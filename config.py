import os

REQUIRED_VARS = [
    "DB_HOST",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
]

import os
BACKUP_REPORT_SECRET = os.getenv("BACKUP_REPORT_SECRET", "")

def validate_env():
    missing = []

    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise RuntimeError(
            f"Variáveis de ambiente faltando: {', '.join(missing)}"
        )

# Diretório raiz para todos os uploads.
# Em produção: defina UPLOADS_DIR=/var/www/api/uploads (fora do repositório).
# Em dev: padrão é ../uploads relativo ao diretório da API.
UPLOADS_DIR = os.getenv(
    "UPLOADS_DIR",
    os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
    )
)

AVATAR_DIR  = os.path.join(UPLOADS_DIR, "avatars")
TICKETS_DIR = os.path.join(UPLOADS_DIR, "tickets")