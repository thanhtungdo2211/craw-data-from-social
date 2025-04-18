# type: ignore
import sys
sys.path.insert(1, ".")
from logging import Logger

from redis import Redis
from kombu import Connection

from redis.exceptions import ConnectionError
from kombu.exceptions import OperationalError

import config

# redis_client = Redis(
#     host=config.REDIS_HOST,
#     port=int(config.REDIS_PORT),
#     db=int(config.REDIS_DB),
#     password=config.REDIS_PASS
# )

def check_redis_localhost():
    try:
        test_conn = Redis(
            host="localhost",
            port=int(config.REDIS_PORT),
            db=int(config.REDIS_DB),
            password=config.REDIS_PASS
        )
        test_conn.ping()
        test_conn.close()
        return True
    except:
        return False
    
REDIS_HOST = "localhost" if check_redis_localhost() else config.REDIS_HOST

redis_client = Redis(
    host=REDIS_HOST,
    port=int(config.REDIS_PORT),
    db=int(config.REDIS_DB),
    password=config.REDIS_PASS
)

def is_broker_running(logger: Logger, retries: int = 30) -> bool:
    try:
        conn = Connection(config.CELERY_BROKER_URL)
        conn.ensure_connection(max_retries=retries)
    except OperationalError as e:
        logger.error("Failed to connect to RabbitMQ instance at %s", config.CELERY_BROKER_URL) # noqa
        logger.error(str(e))
        return False
    conn.close()
    return True


def is_backend_running(logger: Logger) -> bool:
    try:
        conn = Redis(
            host=config.REDIS_HOST,
            port=int(config.REDIS_PORT),
            db=int(config.REDIS_DB),
            password=config.REDIS_PASS
        )
        conn.client_list()  # Must perform an operation to check connection.
    except ConnectionError as e:
        logger.error("Failed to connect to Redis instance at %s", config.CELERY_RESULT_BACKEND) # noqa
        logger.error(repr(e))
        return False
    conn.close()
    return True