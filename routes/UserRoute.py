



from fastapi import APIRouter

from controllers.UserController import SignIn, authCheck, signup


userRouter = APIRouter()


userRouter.post("/signin")(SignIn)
userRouter.post("/signup")(signup)
userRouter.get("/auth")(authCheck)
