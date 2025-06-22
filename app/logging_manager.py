import logging
from logging import Logger


class SingletonLogger:
    _instance: Logger = None

    @staticmethod
    def get_instance():
        if SingletonLogger._instance is None:
            logger = logging.getLogger("AppLogger")
            logger.setLevel(logging.DEBUG)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            console_handler.setFormatter(formatter)

            logger.addHandler(console_handler)

            SingletonLogger._instance = logger

        return SingletonLogger._instance


logger = SingletonLogger.get_instance()