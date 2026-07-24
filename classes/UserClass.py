from pydantic import BaseModel, EmailStr


class SigninRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserData(BaseModel):
    username: str
    email: EmailStr
    role: str = "user"
    avarta: str = ""


class SigninResponse(BaseModel):
    success: bool
    message: str
    user: UserData | None = None
    token: str | None = None


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: UserData | None = None
    token: str | None = None