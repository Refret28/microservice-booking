import configparser
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text


config = configparser.ConfigParser()
config.read('config.ini')
server = config['BD INFO']['SERVER']
username = config['BD INFO']['USERNAME']
driver = config['BD INFO']['DRIVER']


class DB_connection:
    def __init__(self, db_name):
        self.username = username
        self.server = server
        self.db_name = db_name
        self.driver = driver
        self.database_url = (
            f"mssql+aioodbc://{self.username}@{self.server}/{self.db_name}?driver={self.driver}&trusted_connection=yes"
        )
        self.engine = create_async_engine(self.database_url, echo=True)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def get_session(self):
        async with self.session_maker() as session:
            yield session

    async def execute_query(self, query, params=None):
        async with self.session_maker() as session:
            result = await session.execute(text(query), params)
            return result.fetchall()

    async def close(self):
        await self.engine.dispose()
