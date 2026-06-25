# task de background que consome alertas do worker e empurra pro dashboard

import asyncio
import json

import redis.exceptions
from pydantic import ValidationError

from server import config
from server.schemas.models import AlertFrame


async def listen_worker_alerts(client, manager, alerts):
    # assina alerts_channel, guarda no store (p/ refresh) e faz broadcast
    backoff = 1
    while True:
        try:
            pubsub = client.pubsub()
            await pubsub.subscribe(config.ALERTS_CHANNEL)
            backoff = 1
            # loop bloqueante consumindo mensagens do canal
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    frame = json.loads(message["data"])
                    # valida o contrato do alerta antes de repassar
                    AlertFrame.model_validate(frame)
                except (json.JSONDecodeError, TypeError, ValidationError):
                    # alerta malformado, descarta
                    continue
                # guarda (atribui alert_id) para reenviar no snapshot do refresh
                alerts.add(frame)
                await manager.broadcast(frame)
        except (redis.exceptions.ConnectionError, OSError):
            # perdeu o redis: reassina com backoff exponencial
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 20)
