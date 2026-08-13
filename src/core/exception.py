import logging
import traceback
from fastapi import Request, status, FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("omni_english")

def setup_exception_handlers(app: FastAPI):
    
    # 1. Bắt các lỗi chủ động raise 
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            f"[HTTP {exc.status_code}] {request.method} {request.url} → {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "status_code": exc.status_code
            },
        )

    # 2. Bắt lỗi Validation DTO 
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        error_msg = errors[0].get("msg") if errors else "Dữ liệu gửi lên không hợp lệ"
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": f"Lỗi dữ liệu: {error_msg}",
                "errors": errors, 
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        tb = traceback.format_exc()
        logger.error(
            f"[UNHANDLED ERROR] {request.method} {request.url}\n"
            f"Exception: {type(exc).__name__}: {exc}\n"
            f"Traceback:\n{tb}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": f"Lỗi hệ thống: {type(exc).__name__}: {str(exc)}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            },
        )