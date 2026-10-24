from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.database import get_users
from app.settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ✅ auto_error=False stops HTTPBearer from raising a bare 403 before CORS runs
security = HTTPBearer(auto_error=False)

JWT_SECRET = settings.jwt_secret
JWT_EXPIRE_MINUTES = settings.jwt_expire_minutes
ALGO = "HS256"


class LoginBody(BaseModel):
    username: str
    password: str


def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGO)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if creds is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[ALGO])
        return {"username": payload["sub"], "role": payload["role"]}
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/login")
def login(body: LoginBody):
    user = get_users().find_one({"username": body.username})
    if not user or not user.get("active", True):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not pwd_ctx.verify(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["username"], user.get("role", "user"))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "role": user.get("role", "user"),
            "name": user.get("name", user["username"]),
            "division": user.get("division", None),
        },
    }


@router.get("/me")
def me(current=Depends(get_current_user)):
    return current