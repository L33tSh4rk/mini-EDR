# publisher: descarrega o buffer de eventos em lote no redis via rpush

import asyncio
import json

import redis.exceptions

from agent.core import buffer, config


async def _drain(queue):
    # esvazia a queue retornando todos os eventos acumulados
    batch = []
    while not queue.empty():
        batch.append(queue.get_nowait())
    return batch


async def send_events_batch(state, queue, client):
    # loop infinito que a cada flush_interval empurra o lote acumulado
    backoff = 1
    while True:
        await asyncio.sleep(config.FLUSH_INTERVAL)
        batch = await _drain(queue)
        if not batch:
            # sem eventos: apenas confirma que o redis responde (mantem last_redis_ok)
            try:
                await client.ping()
                state.mark_redis_ok()
                backoff = 1
            except (redis.exceptions.ConnectionError, OSError):
                # redis fora do ar: watchdog cuida do isolamento
                pass
            continue
        try:
            # serializa o lote como array json e enfileira no redis
            payload = json.dumps(batch)
            await client.rpush(config.TELEMETRY_QUEUE, payload)
            state.mark_redis_ok()
            backoff = 1
        except (redis.exceptions.ConnectionError, OSError) as exc:
            # falha de conexao: devolve eventos a queue e tenta de novo com backoff
            print(f"[publisher] falha no rpush ({exc}), retry em {backoff}s")
            for event in batch:
                # re-enfileira respeitando o limite (dropa com log se cheia)
                buffer.enqueue(queue, event)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, config.MAX_BACKOFF)
