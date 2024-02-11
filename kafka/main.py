import json
from aiokafka import AIOKafkaProducer
from app import settings


async def get_kafka_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers=[settings.KAFKA_URL],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()
