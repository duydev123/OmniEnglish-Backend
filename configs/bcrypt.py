import bcrypt




def HashPassword(password: str) -> str:

    pwd_bytes = password.encode('utf-8')
   
    salt = bcrypt.gensalt(10)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')



def VerifyPassword(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')


    return bcrypt.checkpw(password_bytes, hashed_bytes)