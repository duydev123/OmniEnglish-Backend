from datetime import datetime, timedelta, timezone
import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt



from fastapi import status



SECRET_KEY = os.getenv("SECRET_KEY")
security = HTTPBearer()

def CreateToken(user: dict) -> str:
 
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



    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return token


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        print("Token is expire")
        return None
    except jwt.InvalidTokenError:
        print("Token not valid")
        return None
    


  
async def Protect(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials 
    
    payload = decode_token(token)    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn!"
        )
    
    return payload  