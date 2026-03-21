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

def validate_env():
    missing = []
    
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)
            
    if missing:
        raise RuntimeError(
            f"Variáveis de ambiente faltando: {', '.join(missing)}"
        )