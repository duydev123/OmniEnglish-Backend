from fastapi import Depends, HTTPException, status
from .dto.user_dto import AuthResponse, SigninRequest, SigninResponse, SignupRequest, UserData
from .user_util import UserUtil
from models.UserModel import UserModel

class UserService:
    @staticmethod
    async def SignIn(data: SigninRequest) -> SigninResponse:
            user = await UserModel.find_one(UserModel.email == data.email)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email not found!"
                )
            
            if not UserUtil.VerifyPassword(data.password, user.password):
                raise HTTPException(
                                    status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Password Incorrect!"
                                )
            
            token = UserUtil.CreateToken(user)

            return SigninResponse(
                success=True,
                message="Login successfully!",
                user=UserData(
                    username=user.username,
                    email=user.email,
                    role=getattr(user, "role", "user"),
                    avarta=getattr(user, "avartar", "") # Sửa thành avartar
                ),
                token=token
            )



    @staticmethod
    async def signup(data: SignupRequest) -> AuthResponse:

            existingUser = await UserModel.find_one(UserModel.email == data.email)
            if existingUser:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account exist!"
                )

            
            hashPass = UserUtil.HashPassword(data.password)
            newUser = UserModel(
                username=data.username,
                email=data.email,
                password=hashPass,
                role="user",
                avartar="" 
            )
            await newUser.insert()
            token = UserUtil.CreateToken(newUser)
            return AuthResponse(
                success=True,
                message="Create account successfully!",
                user=UserData(
                    username=newUser.username,
                    email=newUser.email,
                    role=newUser.role,
                    avarta=newUser.avartar
                ),
                token=token
            )

    @staticmethod
    async def authCheck(currentUser: dict) -> AuthResponse:

            userId = currentUser.get("_id")
            user = await UserModel.get(userId)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Auth not Found!"
                )
            
            return AuthResponse(
                success=True,
                message="Auth found successfully!",
                user=UserData(
                    username=user.username,
                    email=user.email,
                    role=getattr(user, "role", "user"),
                    avarta=getattr(user, "avartar", "")
                )
            )

