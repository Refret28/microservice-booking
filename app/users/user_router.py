import configparser
from datetime import timedelta, datetime
import json
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends, Form, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from aiokafka import AIOKafkaProducer
from starlette.templating import _TemplateResponse

from logging_manager import logger
from db_conn import DB_connection
from users.db_manager import UserRepository
from users.user_schemes import SLoginForm, SRegisterForm, SBookingData, Token, SUser, SCarInfoForm
from users.db_manager import ACCESS_TOKEN_EXPIRE_MINUTES, oauth2_scheme

router = APIRouter()
templates = Jinja2Templates(directory="templates")

config = configparser.ConfigParser()
config.read('config.ini')
server = config['BD INFO']['USER_DB']
pay_server = config['BD INFO']['PAY_DB']
kafka_server = config['KAFKA SETTINGS']['KAFKA_SERVER']
topic_name = config['KAFKA SETTINGS']['TOPIC_NAME']

latest_booking_for_user: dict[int, int] = {}

user_db = DB_connection(server)
pay_db = DB_connection(pay_server)

def get_user_repository() -> UserRepository:
    return UserRepository(user_db)

async def send_to_kafka(user_id: int, booking_id: int, amount: float) -> None:
    producer = AIOKafkaProducer(bootstrap_servers=kafka_server)
    await producer.start()
    try:
        message = {"user_id": user_id, "booking_id": booking_id, "amount": amount}
        message_bytes = json.dumps(message).encode('utf-8')
        await producer.send_and_wait(topic_name, message_bytes)
        logger.info(f"Сообщение отправлено в Kafka: {message}")
    except Exception as e:
        logger.error(f"Ошибка отправки в Kafka: {e}")
    finally:
        await producer.stop()

@router.get("/secure-data")
async def secure_data(token: str = Depends(oauth2_scheme)):
    return {"message": "Secure data accessed"}

@router.get("/login", response_class=HTMLResponse)
async def get_login(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_user_repository)
):
    try:
        user = await user_repo.authenticate_user(form_data.username, form_data.password)
        access_token = await user_repo.create_access_token(data={"sub": user.Email})
        redirect_url = "/admin/dashboard" if user.RoleName == "Admin" else f"/main_page?user_id={user.UserID}"
        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        logger.info(f"Успешный вход пользователя: {user.Email}, роль: {user.RoleName}, перенаправление на {redirect_url}")
        return response
    except HTTPException as e:
        logger.error(f"Ошибка входа: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Неожиданная ошибка при входе: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return RedirectResponse(url="/login", status_code=302)

@router.get("/register", response_class=HTMLResponse)
async def get_register(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    repository: UserRepository = Depends(get_user_repository)
):
    data = SRegisterForm(username=username, email=email, phone=phone, password=password)
    logger.info(f"Получены данные для регистрации: username={username}, email={email}, phone={phone}")
    try:
        user_id = await repository.register_user(data)
        access_token = await repository.create_access_token({"sub": data.email})
        response = RedirectResponse(url=f"/main_page?user_id={user_id}", status_code=302)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        logger.info(f"Пользователь {username} успешно зарегистрирован, ID: {user_id}, токен создан")
        return response
    except ValueError as e:
        logger.error(f"Ошибка регистрации: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неизвестная ошибка регистрации: {str(e)}")
        raise HTTPException(status_code=500, detail="Произошла ошибка при регистрации")

@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    repository: UserRepository = Depends(get_user_repository)
) -> Token:
    user = await repository.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные данные для входа",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = await repository.create_access_token(
        data={"sub": user.Email}
    )
    return Token(access_token=access_token, token_type="bearer")

@router.get("/users/me/", response_model=SUser)
async def read_users_me(
    current_user: Annotated[SUser, Depends(get_user_repository().get_current_active_user)],
):
    return current_user

@router.get("/main_page", response_class=HTMLResponse)
async def main_page(request: Request, user_id: int, repository: UserRepository = Depends(get_user_repository)) -> _TemplateResponse:
    try:
        username = await repository.get_username(user_id)
        occupied_parking = await repository.check_available_parking_spots()
        cancellation_info = await repository.check_cancelled_bookings(user_id)
        
        show_modal = len(occupied_parking) > 0
        modal_class = "show" if show_modal else "hide"
        show_cancellation_modal = cancellation_info["show_cancellation_modal"]
        cancellation_message = cancellation_info["cancellation_message"]

        return templates.TemplateResponse(
            "main.html",
            {
                "request": request,
                "username": username,
                "user_id": user_id,
                "show_modal": show_modal,
                "modal_class": modal_class,
                "occupied_parking": occupied_parking,
                "show_cancellation_modal": show_cancellation_modal,
                "cancellation_message": cancellation_message
            }
        )
    except HTTPException as e:
        logger.error(f"Ошибка при загрузке main_page: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке main_page: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при загрузке главной страницы")

@router.get("/api/parking_spots")
async def get_parking_spots(location: str, repository: UserRepository = Depends(get_user_repository)):
    try:
        spots = await repository.get_parking_spots(location)
        logger.info(f"Возвращенные места для {location}: {spots}")
        return spots
    except Exception as e:
        logger.error(f"Ошибка при получении парковочных мест: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при загрузке парковочных мест")

@router.get("/parking_prices")
async def get_parking_prices(repository: UserRepository = Depends(get_user_repository)):
    try:
        prices = await repository.get_parking_prices()
        return prices
    except Exception as e:
        logger.error(f"Ошибка при получении цен: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при загрузке цен")

@router.get("/user_acc/{user_id}", response_class=_TemplateResponse)
async def get_user_account(
    request: Request,
    user_id: int,
    repository: UserRepository = Depends(get_user_repository)
) -> _TemplateResponse:
    try:
        user_info = await repository.get_user_info(user_id)
        if not user_info.get("bookings"):
            user_info["bookings"] = []

        return templates.TemplateResponse(
            "user_acc.html",
            {
                "request": request,
                "username": user_info["username"],
                "email": user_info["email"],
                "phone": user_info["phone"],
                "user_id": user_id,
                "bookings": user_info["bookings"],  
            }
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

@router.delete("/cancel_booking/{booking_id}")
async def cancel_booking(booking_id: int, repository: UserRepository = Depends(get_user_repository)):
    try:
        await repository.cancel_booking(booking_id)
    except ValueError:
        raise HTTPException(status_code=404)

@router.post("/book", status_code=201)
async def create_booking(booking_data: dict, repository: UserRepository = Depends(get_user_repository)):
    try:
        print(f"Данные о брони: {booking_data}")

        user_id = booking_data.get("user_id")
        address = booking_data.get("address")
        floor = booking_data.get("floor")
        spot_number = booking_data.get("spot_number")
        start_datetime = booking_data.get("start_time")
        end_datetime = booking_data.get("end_time")

        if not all([user_id, address, spot_number, start_datetime, end_datetime]):
            raise HTTPException(status_code=400, detail="Отсутствуют обязательные поля для бронирования.")

        spot_number = str(spot_number)
        floor = str(floor) if floor is not None else None

        start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="Время окончания должно быть позже времени начала.")

        prices = await repository.get_parking_prices()
        price_data = next((p for p in prices if p["address"] == address), None)
        if not price_data:
            raise HTTPException(status_code=400, detail="Неверный адрес парковки.")

        price_per_minute = price_data["price_per_minute"]
        amount = duration_minutes * price_per_minute

        spots = await repository.get_parking_spots(f"{0.0}|{address}")
        logger.info(f"Полученные места для {address}: {spots}")

        has_floors = any(s["floor"] is not None for s in spots)
        
        if has_floors and floor is not None:
            spot = next((s for s in spots if s["spot_number"] == spot_number and s["floor"] == floor and s["is_available"]), None)
        else:
            spot = next((s for s in spots if s["spot_number"] == spot_number and s["floor"] is None and s["is_available"]), None)

        if not spot:
            floor_str = f"на этаже {floor}" if floor is not None else "без этажа"
            logger.error(f"Место {spot_number} {floor_str} недоступно для адреса {address}")
            raise HTTPException(status_code=400, detail=f"Место {spot_number} {floor_str} недоступно.")

        booking_data_for_db = SBookingData(
            user_id=user_id,
            address=address,
            floor=None if not has_floors else floor,  
            spot_number=spot_number,
            start_datetime=start_datetime,
            end_datetime=end_datetime
        )

        booking_id, spot_num = await repository.add_booking(booking_data_for_db)
        await send_to_kafka(user_id, booking_id, round(amount, 2))

        latest_booking_for_user[user_id] = booking_id
        print("\n\n", latest_booking_for_user, "\n\n")

        response = {
            "message": "Бронирование успешно создано",
            "booking_id": booking_id,
            "spot_number": spot_num,
            "amount": round(amount, 2),
        }
        return response

    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Произошла непредвиденная ошибка.")
    
@router.post("/cars")
async def add_car(
    car_info: SCarInfoForm,
    repository: UserRepository = Depends(get_user_repository)
):
    user_id = car_info.user_id
    print(user_id)
    print("\n\n", latest_booking_for_user, "\n\n")
    booking_id = latest_booking_for_user.get(user_id)
    print(booking_id)
    if booking_id is None:
        raise HTTPException(status_code=404, detail="Бронирование для пользователя не найдено")

    car_info.booking_id = booking_id  

    try:
        await repository.add_car_info(car_info)
        
        return {"message": "Автомобиль успешно сохранён"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении автомобиля: {str(e)}")
