import logging

import pika

logger = logging.getLogger(__name__)


def get_rabbit_channel(
    username,
    password,
    host,
):
    """
    Establishes a new blocking connection to RabbitMQ and returns a channel.

    Args:
        exchange_name (str): Name of the exchange to declare.
        exchange_type (str): Type of the exchange (default: topic).

    Returns:
        tuple: (connection, channel)
    """
    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(host=host, credentials=credentials)

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        return connection, channel
    except Exception:
        logger.exception(
            "Failed to connect to RabbitMQ",
            extra={"host": host, "username": username},
        )
