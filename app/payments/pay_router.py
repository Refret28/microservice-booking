import configparser
import asyncio
import json

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.background import BackgroundTasks
from aiokafka import AIOKafkaConsumer
from starlette.templating import _TemplateResponse
from pydantic import BaseModel

from logging_manager import logger
from db_conn import DB_connection
from payments.db_manager import PayRepository


router = APIRouter()

templates = Jinja2Templates(directory="templates")

config = configparser.ConfigParser()
config.read('config.ini')
server = config['BD INFO']['PAY_DB']
kafka_server = config['KAFKA SETTINGS']['KAFKA_SERVER']
topic_name = config['KAFKA SETTINGS']['TOPIC_NAME']
telegram_bot_username = config['API TOKEN']['BOT_USERNAME'] 

user_booking_cache = {}

pay_db = DB_connection(server)

def get_pay_repository() -> PayRepository:
    return PayRepository(pay_db)

async def start_consumer() -> AIOKafkaConsumer:
    for _ in range(5):  
        try:
            consumer = AIOKafkaConsumer(
                topic_name,
                bootstrap_servers=kafka_server,
                group_id="my-group",
                session_timeout_ms=40000, 
                heartbeat_interval_ms=10000,
                retry_backoff_ms=200,  
                request_timeout_ms=10000,  
                auto_offset_reset="earliest",
                enable_auto_commit=False
            )
            await consumer.start()
            logger.info("Консьюмер начал работу.")
            return consumer
        except Exception as e:
            logger.info(f"Повторная попытка подключения из-за ошибки: {e}")
            await asyncio.sleep(2)
    raise Exception("Не удалось подключиться к Kafka после нескольких попыток.")

async def consume_from_kafka(user_id: int) -> None:
    global user_booking_cache
    
    consumer = await start_consumer()
    try:
        timeout = 15 
        start_time = asyncio.get_event_loop().time()

        async for msg in consumer:
            try:
                message = json.loads(msg.value.decode('utf-8'))
                msg_user_id = message.get("user_id")
                booking_id = message.get("booking_id")
                amount = message.get("amount")
                logger.info(f"Получено сообщение из Kafka: user_id={msg_user_id}, booking_id={booking_id}, amount={amount}")

                user_booking_cache[msg_user_id] = {
                    "booking_id": booking_id,
                    "amount": amount
                }
                logger.info(f"Сохранено в кэш: {user_booking_cache}")

                await consumer.commit()

                if msg_user_id == user_id:
                    break
            except json.JSONDecodeError:
                logger.error(f"Ошибка при декодировании сообщения: {msg.value}")
                await consumer.commit()

            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.info("Тайм-аут ожидания сообщений из Kafka.")
                break
    finally: 
        await consumer.stop()

@router.get("/pay/{user_id}", response_class=HTMLResponse)
async def get_pay(request: Request, user_id: int):
    if user_id not in user_booking_cache:
        logger.info(f"Ожидание сообщения Kafka для user_id={user_id}")
        await consume_from_kafka(user_id)
    
    if user_id not in user_booking_cache:
        raise HTTPException(status_code=400, detail="Данные бронирования не найдены")

    data = user_booking_cache[user_id]
    amount = data['amount']
    booking_id = data.get('booking_id')  

    logger.info(f"Рендеринг pay.html для user_id={user_id}, amount={amount}, booking_id={booking_id}")

    response = templates.TemplateResponse(
        "pay.html",
        {"request": request, "user_id": user_id, "amount": amount, "booking_id": booking_id}
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    logger.info(f"Шаблон pay.html отправлен с amount={amount} и booking_id={booking_id}")
    return response

@router.post("/pay")
async def process_payment(
    data: dict,
    background_tasks: BackgroundTasks,
    pay_repo: PayRepository = Depends(get_pay_repository),
):
    try:
        user_id = data.get("user_id")

        try:
            user_id = int(user_id) if user_id else None
        except (ValueError, TypeError):
            logger.error(f"Неверный формат user_id: {user_id}")
            raise HTTPException(status_code=400, detail="Неверный формат идентификатора пользователя")

        logger.info(f"POST /pay: user_id={user_id}, cache={user_booking_cache}")

        if not user_booking_cache or user_id not in user_booking_cache:
            logger.error(f"Данные бронирования не найдены для user_id={user_id}")
            raise HTTPException(status_code=400, detail="Данные бронирования не найдены")
        
        cache_data = user_booking_cache[user_id]
        booking_id = cache_data.get("booking_id")
        amount = cache_data.get("amount")
        
        if not user_id or not booking_id:
            logger.error(f"Отсутствуют user_id или booking_id: user_id={user_id}, booking_id={booking_id}")
            raise HTTPException(status_code=400, detail="User ID или Booking ID не найдены")

        telegram_url = f"https://t.me/{telegram_bot_username}?start=pay_{booking_id}_{amount}_{user_id}"
        logger.info(f"Сгенерирована ссылка для оплаты: {telegram_url}")

        return {"telegram_url": telegram_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Произошла ошибка при обработке данных: {str(e)}")


@router.post("/save_payment")
async def save_payment(
    data: dict,
    pay_repo: PayRepository = Depends(get_pay_repository)
):
    try:
        booking_id = data.get("booking_id")
        amount = data.get("amount")
        telegram_transaction_id = data.get("telegram_transaction_id")
        user_id = data.get("user_id")

        if not all([booking_id, amount, telegram_transaction_id, user_id]):
            raise HTTPException(status_code=400, detail="Отсутствуют обязательные данные платежа")

        user_id = int(user_id)
        transaction_id = await pay_repo.add_telegram_payment(booking_id, amount, telegram_transaction_id, user_id)
        logger.info(f"Платеж сохранен: booking_id={booking_id}, transaction_id={transaction_id}")

        user_booking_cache.pop(user_id, None)
        logger.info(f"Кэш очищен для user_id={user_id}")

        return RedirectResponse(url=f"/waiting/{user_id}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при сохранении платежа: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при сохранении платежа")

@router.post("/cancel_booking/{user_id}")
async def cancel_booking(user_id: int, pay_repo: PayRepository = Depends(get_pay_repository)):
    try:
        if user_id not in user_booking_cache:
            raise HTTPException(status_code=400, detail="Бронирование не найдено")
        
        booking_id = user_booking_cache[user_id].get("booking_id")
        user_booking_cache.pop(user_id, None)
        logger.info(f"Бронирование {booking_id} для user_id={user_id} отменено")
        return {"message": "Бронирование успешно отменено"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отмене бронирования: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при отмене бронирования")

@router.get("/waiting/{user_id}", response_class=HTMLResponse)
async def payment_success(request: Request, user_id: int) -> _TemplateResponse:
    response = templates.TemplateResponse("waiting.html", {"request": request, "user_id": user_id})
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@router.get("/booking_details/{booking_id}", response_class=HTMLResponse)
async def get_booking_details(request: Request, booking_id: str, pay_repo: PayRepository = Depends(get_pay_repository)):
    try:
        details = await pay_repo.get_booking_details(booking_id)
        if not details:
            raise HTTPException(status_code=404, detail="Данные о бронировании не найдены")

        logger.info(f"Рендеринг booking_details.html для booking_id={booking_id}")
        logger.info(f"user_id при рендере booking_details.html: {details.get('user_id')}")
        response = templates.TemplateResponse(
            "booking_details.html",
            {
                "request": request,
                "user_id": details.get("user_id", None),
                "payment_status": details.get("payment_status", "Не указано"),
                "amount": details.get("amount"),
                "transaction_id": details.get("transaction_id", "Не указано")
            }
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        logger.info(f"Шаблон booking_details.html отправлен для booking_id={booking_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении данных о бронировании: {e}")
        raise HTTPException(status_code=500, detail="Произошла ошибка при получении данных")
    
