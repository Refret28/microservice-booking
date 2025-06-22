from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from starlette.templating import _TemplateResponse
from typing import List, Dict
from logging_manager import logger
from admin.db_manager import AdminRepository
from admin.admin_schemes import ParkingLocationSchema, ParkingSpotSchema, AdminUserSchema, UpdatePriceSchema, BookingSchema
from db_conn import DB_connection
import configparser
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

config = configparser.ConfigParser()
config.read('config.ini')
user_server = config['BD INFO']['USER_DB']
pay_server = config['BD INFO']['PAY_DB']
user_db = DB_connection(user_server)
pay_db = DB_connection(pay_server)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_admin_repository() -> AdminRepository:
    return AdminRepository(user_db, pay_db)

async def get_token_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Токен не найден в cookies")
    return token

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    request: Request,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
) -> _TemplateResponse:
    parkings = await get_admin_repository().get_parkings()
    logger.info(f"Парковки для dashboard: {parkings}")
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "parkings": parkings}
    )

@router.get("/admin/parkings", response_model=List[ParkingLocationSchema])
async def get_parkings(
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    return await get_admin_repository().get_parkings()

@router.get("/admin/spots/{location_id}")
async def get_spots(
    location_id: int,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
) -> Dict:
    return await get_admin_repository().get_spots_by_parking(location_id)

@router.post("/admin/spots/{spot_id}/reserve")
async def reserve_spot(
    spot_id: int,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    await get_admin_repository().update_spot_status(spot_id, False)
    return {"message": f"Место {spot_id} зарезервировано"}

@router.post("/admin/spots/{spot_id}/free")
async def free_spot(
    spot_id: int,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    try:
        await get_admin_repository().update_spot_status(spot_id, True)
        return {"message": f"Место {spot_id} освобождено, связанная бронь отменена"}
    except HTTPException as e:
        logger.error(f"Ошибка при освобождении места {spot_id}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Неожиданная ошибка при освобождении места {spot_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при освобождении места")

@router.post("/admin/spots/{spot_id}/update_price")
async def update_spot_price(
    spot_id: int,
    price_data: UpdatePriceSchema,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    await get_admin_repository().update_spot_price(spot_id, price_data.price)   
    return {"message": f"Цена места {spot_id} обновлена"}

@router.get("/admin/users", response_model=List[AdminUserSchema])
async def get_users(
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    users = await get_admin_repository().get_all_users()
    logger.info(f"Получен список пользователей: {len(users)} записей")
    return users

@router.get("/admin/users/{user_id}/bookings", response_model=List[BookingSchema])
async def get_user_bookings(
    user_id: int,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    bookings = await get_admin_repository().get_user_bookings(user_id)
    logger.info(f"Получено {len(bookings)} бронирований для пользователя {user_id}")
    return bookings

@router.post("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    status_data: dict,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    status = status_data.get("status")
    if status not in ["White", "Black"]:
        raise HTTPException(status_code=400, detail="Недопустимое значение статуса")
    await get_admin_repository().update_user_status(user_id, status)
    return {"message": f"Статус пользователя {user_id} обновлен на {status}"}

@router.get("/admin/analytics/parkings")
async def get_parkings_analytics(
    start_date: datetime,
    end_date: datetime,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    analytics = await get_admin_repository().get_parkings_analytics(start_date, end_date)
    logger.info(f"Получена аналитика парковок за период {start_date} - {end_date}: {analytics}")
    return analytics

@router.get("/admin/analytics/spots")
async def get_spots_analytics(
    start_date: datetime,
    end_date: datetime,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    analytics = await get_admin_repository().get_spots_analytics(start_date, end_date)
    logger.info(f"Получена аналитика мест за период {start_date} - {end_date}: {analytics}")
    return analytics

@router.get("/admin/analytics/revenue")
async def get_revenue_analytics(
    start_date: datetime,
    end_date: datetime,
    current_admin: AdminUserSchema = Depends(lambda: get_admin_repository().get_current_admin(get_token_from_cookie))
):
    analytics = await get_admin_repository().get_revenue_analytics(start_date, end_date)
    logger.info(f"Получена аналитика доходов за период {start_date} - {end_date}: {analytics}")
    return analytics

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response