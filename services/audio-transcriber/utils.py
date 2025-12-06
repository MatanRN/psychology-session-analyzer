BUCKET_NAME = "sessions"
EXCHANGE_NAME = "events"
MAX_DELIVERY_COUNT = 3


def setup_rabbit_entities(channel):
    """
    Establishes a new blocking connection to RabbitMQ and returns a channel.

    This function creates a fresh connection for each request to ensure thread safety
    and avoid connection closure issues typical with long-lived connections in
    threaded environments. It also ensures the target exchange exists.

    Returns:
        tuple: A tuple containing (connection, channel).
            - connection (pika.BlockingConnection): The active RabbitMQ connection.
            - channel (pika.channel.Channel): The active channel for publishing.
    """

    # Set up dead letter hanlding
    channel.exchange_declare(
        exchange="dead_letter_exchange", exchange_type="direct", durable=True
    )
    channel.queue_declare(queue="dlq_audio_transcriber", durable=True)
    channel.queue_bind(
        queue="dlq_audio_transcriber",
        exchange="dead_letter_exchange",
        routing_key="audio.transcription.failed",
    )
    # Ensure exchanges exists - idempotent
    channel.exchange_declare(
        exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
    )
    # Ensure queue exists - idempotent
    arguments = {
        "x-queue-type": "quorum",
        "x-delivery-limit": MAX_DELIVERY_COUNT,
        "x-dead-letter-exchange": "dead_letter_exchange",
        "x-dead-letter-routing-key": "audio.transcription.failed",
    }
    channel.queue_declare(
        queue="audio_transcription_queue",
        durable=True,
        arguments=arguments,
    )
    channel.queue_bind(
        queue="audio_transcription_queue",
        exchange=EXCHANGE_NAME,
        routing_key="audio.extraction.completed",
    )
