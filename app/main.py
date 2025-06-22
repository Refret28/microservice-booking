from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from users.user_router import router as user_router
from payments.pay_router import router as pay_router
from admin.admin_router import router as admin_router
from scheduler import setup_scheduler, scheduler, user_db_connection, pay_db_connection
from logging_manager import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_scheduler()
    
    try:
        yield
    finally:
        await shutdown()

async def shutdown():
    logger.info("Shutting down application")
    scheduler.shutdown(wait=False)  
    await user_db_connection.close() 
    await pay_db_connection.close()
    logger.info("Application shutdown complete")

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(user_router)
app.include_router(pay_router)
app.include_router(admin_router)

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)