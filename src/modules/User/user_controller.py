from fastapi import APIRouter, status, Depends
from .user_service import UserService
from .dto.user_dto import SigninRequest, SignupRequest, SigninResponse, AuthResponse
from .user_util import UserUtil

routerUser = APIRouter(prefix="/users", tags=["Users"])
userService = UserService()

@routerUser.post("/signin", response_model=SigninResponse, status_code=status.HTTP_200_OK)
async def sign_in(dto: SigninRequest):
    return await userService.SignIn(dto)

@routerUser.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(dto: SignupRequest):
    return await userService.signup(dto)

@routerUser.get("/auth", response_model=AuthResponse)
async def check_auth(current_user: dict = Depends(UserUtil.Protect)):
    return await userService.authCheck(current_user)