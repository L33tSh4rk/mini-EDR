# task de background que marca agentes offline por falta de heartbeat

import asyncio

from server import config
from server.api import frames


async def reap_offline_agents(registry, manager):
    # varre periodicamente e notifica dashboard dos agentes que cairam
    while True:
        await asyncio.sleep(config.REAPER_INTERVAL)
        for agent in registry.expire(config.HEARTBEAT_TIMEOUT):
            await manager.broadcast(frames.status_frame(agent))
