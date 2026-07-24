from fastapi import Depends

from classes.UserClass import (
    AuthResponse, 
    SigninRequest, 
    SigninResponse, 
    SignupRequest, 
    UserData
)
from configs.bcrypt import HashPassword, VerifyPassword
from configs.jtw import CreateToken, Protect
from models import UserModel


async def SignIn(data: SigninRequest) -> SigninResponse:
    try:
        user = await UserModel.find_one({"email": data.email})
        if not user:
            return SigninResponse(
                success=False, 
                message="Email not found!"
            )

        if not VerifyPassword(data.password, user.password):
            return SigninResponse(
                success=False, 
                message="Password Incorrect!"
            )

        token = CreateToken(user)

        return SigninResponse(
            success=True,
            message="Login successfully!",
            user=UserData(
                username=user.username,
                email=user.email,
                role=getattr(user, "role", "user"),
                avarta=getattr(user, "avarta", "")
            ),
            token=token
        )

    except Exception as e:
        print(f"SignIn error: {e}")
        return SigninResponse(
            success=False, 
            message="Signin failed!"
        )


async def signup(data: SignupRequest) -> AuthResponse:
    try:
        existingUser = await UserModel.find_one({"email": data.email})
        if existingUser:
            return AuthResponse(
                success=False, 
                message="Account exist!"
            )

        hashPass = HashPassword(data.password)

        newUser = UserModel(
            username=data.username,
            email=data.email,
            password=hashPass,
            role="user",
            avarta=""
        )
        await newUser.insert()

        token = CreateToken(newUser)

        return AuthResponse(
            success=True,
            message="Create accout successfully!",
            user=UserData(
                username=newUser.username,
                email=newUser.email,
                role=newUser.role,
                avarta=newUser.avarta
            ),
            token=token
        )

    except Exception as e:
        print(f"Signup error: {e}")
        return AuthResponse(
            success=False, 
            message="Signup failed!:"
        )


async def authCheck(currentUser: dict = Depends(Protect)) -> AuthResponse:
    try:
        userId = currentUser.get("_id")
        user = await UserModel.get(userId)
        
        if not user:
            return AuthResponse(
                success=False, 
                message="Auth not Found!"
            )

        return AuthResponse(
            success=True,
            message="Auth found successfully!",
            user=UserData(
                username=user.username,
                email=user.email,
                role=getattr(user, "role", "user"),
                avarta=getattr(user, "avarta", "")
            )
        )

    except Exception as e:
        print(f"AuthCheck error: {e}")
        return AuthResponse(
            success=False, 
            message="Auth found error!"
        )