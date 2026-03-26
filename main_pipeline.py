import asyncio
from modulo2_motor_alertas.motor_alertas import alerts_producer
from modulo3_agente_telegram.alerts_notify import alerts_consumer

async def main():
    queue = asyncio.Queue()
    producer_task = asyncio.create_task(alerts_producer(queue))
    consumer_task = asyncio.create_task(alerts_consumer(queue))
    await asyncio.gather(producer_task, consumer_task)

if __name__=="__main__":
    asyncio.run(main())