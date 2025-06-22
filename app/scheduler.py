from apscheduler.schedulers.asyncio import AsyncIOScheduler
import configparser
from datetime import datetime, timedelta

from sqlalchemy import select
from db_conn import DB_connection
from users.user_models import Booking, ParkingSpot
from payments.pay_models import Payment
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')
user_server = config['BD INFO']['USER_DB']
pay_server = config['BD INFO']['PAY_DB']

user_db_connection = DB_connection(db_name=user_server) 
pay_db_connection = DB_connection(db_name=pay_server)

scheduler = AsyncIOScheduler()

async def check_expired_bookings():
    logger.info("Starting check for expired bookings")
    print("Starting check for expired bookings")
    
    async with user_db_connection.session_maker() as user_session:
        async with pay_db_connection.session_maker() as pay_session:
            try:
                stmt = select(Booking)
                result = await user_session.execute(stmt)
                all_bookings = result.scalars().all()
                
                current_time = datetime.now()
                expiration_time = timedelta(minutes=60)
                
                for booking in all_bookings:
                    expiry_time = booking.Created + expiration_time
                    if current_time > expiry_time:
                        pay_stmt = select(Payment).where(Payment.BookingID == booking.BookingID)
                        pay_result = await pay_session.execute(pay_stmt)
                        payment = pay_result.scalars().first()
                        
                        if not payment:
                            logger.info(f"Deleting expired booking: {booking.BookingID}")
                            await user_session.delete(booking)
                            
                            spot_stmt = select(ParkingSpot).where(ParkingSpot.SpotID == booking.SpotID)
                            spot_result = await user_session.execute(spot_stmt)
                            spot = spot_result.scalars().first()
                            if spot:
                                spot.IsAvailable = 1
                                logger.info(f"Parking spot {spot.SpotID} is now available")
                            else:
                                logger.warning(f"No parking spot found for booking {booking.BookingID}")
                
                await user_session.commit()
                logger.info("Expired bookings check completed")
                print("Expired bookings check completed")
            
            except Exception as e:
                logger.error(f"Error during check_expired_bookings: {str(e)}")
                print(f"Error during check_expired_bookings: {str(e)}")
                await user_session.rollback()

async def delete_expired_bookings_by_end_datetime():
    logger.info("Starting check for bookings with expired end_datetime")
    print("Starting check for bookings with expired end_datetime")
    
    async with user_db_connection.session_maker() as user_session:
        try:
            stmt = select(Booking)
            result = await user_session.execute(stmt)
            all_bookings = result.scalars().all()
            
            current_time = datetime.now()
            
            for booking in all_bookings:
                try:
                    end_datetime = datetime.strptime(booking.EndTime, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        end_datetime = datetime.fromisoformat(booking.EndTime)
                    except ValueError as ve:
                        logger.error(f"Invalid end_datetime format for booking {booking.BookingID}: {booking.EndTime}")
                        continue
                
                if end_datetime < current_time:
                    logger.info(f"Deleting booking with expired end_datetime: {booking.BookingID}")
                    await user_session.delete(booking)
                    
                    spot_stmt = select(ParkingSpot).where(ParkingSpot.SpotID == booking.SpotID)
                    spot_result = await user_session.execute(spot_stmt)
                    spot = spot_result.scalars().first()
                    if spot:
                        spot.IsAvailable = 1
                        logger.info(f"Parking spot {spot.SpotID} is now available")
                    else:
                        logger.warning(f"No parking spot found for booking {booking.BookingID}")
            
            await user_session.commit()
            logger.info("Expired end_datetime bookings check completed")
            print("Expired end_datetime bookings check completed")
        
        except Exception as e:
            logger.error(f"Error during delete_expired_bookings_by_end_datetime: {str(e)}")
            print(f"Error during delete_expired_bookings_by_end_datetime: {str(e)}")
            await user_session.rollback()

def setup_scheduler():
    scheduler.add_job(check_expired_bookings, "interval", minutes=5)
    scheduler.add_job(delete_expired_bookings_by_end_datetime, "interval", minutes=5)
    scheduler.start()
    logger.info("Scheduler initialized")