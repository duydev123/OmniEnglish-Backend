import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SECRET_KEY = os.getenv("SECRET_KEY", "OMNI_ENGLISH_SUPER_SECRET_KEY")
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

class UserUtil:
    @staticmethod
    def HashPassword(password: str) -> str:
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(10)
        return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    @staticmethod
    def VerifyPassword(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def CreateToken(user) -> str:
        expiration = datetime.now(timezone.utc) + timedelta(days=1)
        user_id = str(getattr(user, "id", getattr(user, "_id", None)))
        user_email = getattr(user, "email", None)
        
        if isinstance(user, dict):
            user_id = str(user.get("_id", user.get("id")))
            user_email = user.get("email")

        payload = {
            "_id": user_id,
            "email": user_email,
            "exp": expiration,
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> dict | None:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            print("Token is expired")
            return None
        except jwt.InvalidTokenError:
            print("Token not valid")
            return None

    @staticmethod
    async def Protect(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        token = credentials.credentials
        payload = UserUtil.decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ hoặc đã hết hạn!"
            )
        return payload

    @staticmethod
    async def ProtectOptional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)) -> dict | None:
        if not credentials:
            return None
        token = credentials.credentials
        return UserUtil.decode_token(token)