import asyncio
import configparser
import json
import logging
import time
import aiohttp
from aiokafka import AIOKafkaConsumer
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ContentType
from aiogram.filters import Command, CommandStart
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties
from fastapi.responses import RedirectResponse


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


config = configparser.ConfigParser()
config.read("config.ini")

BOT_TOKEN = config["API TOKEN"]["TOKEN"]
PAYMENTS_TOKEN = config["API TOKEN"]["PAYMENTS_TOKEN"]
KAFKA_SERVER = config["KAFKA SETTINGS"]["KAFKA_SERVER"]
TOPIC_NAME = config["KAFKA SETTINGS"]["TOPIC_NAME"]
PAYMENT_SERVER_URL = config["API TOKEN"]["PAYMENT_SERVER_URL"]


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

user_booking_cache = {}

async def start_consumer() -> AIOKafkaConsumer:
    for _ in range(5):
        try:
            consumer = AIOKafkaConsumer(
                TOPIC_NAME,
                bootstrap_servers=KAFKA_SERVER,
                group_id="payment-bot-group",
                session_timeout_ms=40000,
                heartbeat_interval_ms=10000,
                retry_backoff_ms=200,
                request_timeout_ms=10000,
                auto_offset_reset="earliest",
                enable_auto_commit=False
            )
            await consumer.start()
            logger.info("Kafka consumer запущен")
            return consumer
        except Exception as e:
            logger.error(f"Ошибка подключения к Kafka: {e}")
            await asyncio.sleep(2)
    raise Exception("Не удалось подключиться к Kafka после 5 попыток")

async def kafka_listener():
    consumer = await start_consumer()
    try:
        async for msg in consumer:
            try:
                message = json.loads(msg.value.decode('utf-8'))
                if message.get('processed'):
                    await consumer.commit()
                    continue

                user_id = message.get("user_id")
                user_booking_cache[user_id] = {
                    'data': message,
                    'offset': msg.offset
                }
                logger.info(f"Получено и сохранено сообщение из Kafka: user_id={user_id}, message={message}")
                await consumer.commit()
            except json.JSONDecodeError:
                logger.error(f"Ошибка декодирования: {msg.value}")
                await consumer.commit()
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {e}")
                await consumer.commit()
    except Exception as e:
        logger.error(f"Ошибка в kafka_listener: {e}")
    finally:
        await consumer.stop()
        logger.info("Kafka consumer остановлен")

async def consume_from_kafka(user_id: int = None) -> dict:
    timeout = 15
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < timeout:
        if user_id in user_booking_cache:
            return user_booking_cache[user_id]
        
        if user_booking_cache:
            last_user_id = max(user_booking_cache.keys()) 
            logger.info(f"Данные для user_id={user_id} не найдены, возвращаем последнее сообщение для user_id={last_user_id}")
            return user_booking_cache[last_user_id]
        await asyncio.sleep(0.1)
    
    logger.warning(f"Таймаут ожидания данных Kafka для user_id={user_id}")
    return None

@dp.message(Command("start"))
async def handle_buy(message: types.Message):
     await message.answer("👋 Приветствую вас! Для оплаты брони используйте команду /buy")

@dp.message(Command("buy"))
async def handle_buy(message: types.Message):
    try:
        await message.answer("🔍 Ищем доступные бронирования...")
        kafka_data = await consume_from_kafka(message.from_user.id)

        if not kafka_data:
            await message.answer("❌ Нет доступных бронирований")
            return

        booking_data = kafka_data['data']
        await send_payment_invoice(
            chat_id=message.chat.id,
            booking_id=booking_data["booking_id"],
            amount=booking_data["amount"],
            user_id=booking_data["user_id"],
            kafka_offset=kafka_data["offset"]
        )

    except Exception as e:
        logger.error(f"Ошибка в /buy: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке запроса")

@dp.message(CommandStart(deep_link=True))
async def handle_start_with_payment(message: types.Message):
    try:
        start_param = message.get_args()
        if not start_param.startswith("pay_"):
            await message.answer("👋 Привет! Для оплаты брони используйте команду /buy или ссылку от приложения.")
            return
        
        _, booking_id, amount, user_id = start_param.split("_")
        booking_id = int(booking_id)
        amount = float(amount)
        user_id = int(user_id)

        if user_id != message.from_user.id:
            await message.answer("❌ Неверный идентификатор пользователя")
            logger.error(f"Несоответствие user_id: expected={user_id}, actual={message.from_user.id}")
            return

        logger.info(f"Обработка deep link: booking_id={booking_id}, amount={amount}, user_id={user_id}")

        await send_payment_invoice(
            chat_id=message.chat.id,
            booking_id=booking_id,
            amount=amount,
            user_id=user_id,
            kafka_offset=None
        )

    except ValueError:
        await message.answer("❌ Неверный формат ссылки для оплаты")
        logger.error(f"Неверный формат start_param: {start_param}")
    except TelegramBadRequest as e:
        await message.answer(f"❌ Ошибка при создании платежа: {e.message}")
        logger.error(f"Ошибка Telegram: {e}")
    except Exception as e:
        await message.answer("❌ Произошла непредвиденная ошибка")
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)

async def send_payment_invoice(chat_id: int, booking_id: int, amount: float, user_id: int, kafka_offset: int = None):
    try:
        amount_in_cents = int(float(amount) * 100)
        payload = json.dumps({
            "booking_id": booking_id,
            "amount": amount,
            "user_id": user_id,
            "kafka_offset": kafka_offset
        })

        await bot.send_invoice(
            chat_id=chat_id,
            title=f"Оплата бронирования #{booking_id}",
            description=f"Оплата на сумму {amount} RUB",
            provider_token=PAYMENTS_TOKEN,
            currency="RUB",
            prices=[types.LabeledPrice(label="Бронирование", amount=amount_in_cents)],
            payload=payload,
            start_parameter=str(booking_id)
        )
        logger.info(f"Инвойс отправлен: chat_id={chat_id}, booking_id={booking_id}, amount={amount}")
    except Exception as e:
        logger.error(f"Ошибка отправки инвойса: {e}")
        await bot.send_message(chat_id, "❌ Ошибка при отправке инвойса")

@dp.pre_checkout_query(lambda query: True)
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    try:
        await pre_checkout_query.answer(True)
        logger.info(f"Pre-checkout подтвержден для user_id={pre_checkout_query.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при pre-checkout: {e}")
        await pre_checkout_query.answer(False, "Ошибка проверки")

@dp.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):
    payment = message.successful_payment

    try:
        payload = json.loads(payment.invoice_payload)
        booking_id = payload["booking_id"]
        user_id = payload["user_id"]

        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{PAYMENT_SERVER_URL}/save_payment",
                json={
                    "booking_id": booking_id,
                    "amount": payment.total_amount / 100,
                    "telegram_transaction_id": payment.telegram_payment_charge_id,
                    "user_id": user_id
                }
            )
            if response.status != 200:
                logger.error(f"Ошибка сохранения платежа: {await response.text()}")
                await message.answer("❌ Ошибка при сохранении платежа")
                return

        await message.answer(
            f"✅ Платеж на сумму {payment.total_amount // 100} RUB прошел успешно!\n"
            f"Бронирование #{booking_id} подтверждено."
        )

        if user_id in user_booking_cache:
            del user_booking_cache[user_id]
            logger.info(f"Кэш очищен для user_id={user_id}")

    except Exception as e:
        logger.error(f"Ошибка успешного платежа: {e}")
        await message.answer("✅ Платеж прошел, но возникла ошибка при обработке.")

async def main():
    asyncio.create_task(kafka_listener())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())