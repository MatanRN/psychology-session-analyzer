BUCKET_NAME = "sessions"
EXCHANGE_NAME = "events"
MAX_DELIVERY_COUNT = 3


def setup_rabbit_entities(channel):
    """
    Sets up the RabbitMQ entities for the audio extraction service.
    """
    channel.exchange_declare(
        exchange="dead_letter_exchange", exchange_type="direct", durable=True
    )
    channel.queue_declare(queue="dlq_audio_extraction", durable=True)
    channel.queue_bind(
        queue="dlq_audio_extraction",
        exchange="dead_letter_exchange",
        routing_key="audio.extraction.failed",
    )
    # Ensure exchanges exists - idempotent
    channel.exchange_declare(
        exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
    )
    args = {
        "x-queue-type": "quorum",
        "x-delivery-limit": MAX_DELIVERY_COUNT,
        "x-dead-letter-exchange": "dead_letter_exchange",
        "x-dead-letter-routing-key": "audio.extraction.failed",
    }
    # Ensure queue exists - idempotent
    channel.queue_declare(queue="audio_extraction_queue", durable=True, arguments=args)
    # Bind queue to exchange with routing key - idempotent

    channel.queue_bind(
        queue="audio_extraction_queue",
        exchange=EXCHANGE_NAME,
        routing_key="video.upload.completed",
    )
