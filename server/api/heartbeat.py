# listener udp puro dos heartbeats dos agentes

import asyncio

from server import config
from server.api import frames


class HeartbeatProtocol(asyncio.DatagramProtocol):
    # protocolo udp que parseia "ALIVE:{agent_id}" e atualiza presenca

    def __init__(self, registry, manager, loop):
        self.registry = registry
        self.manager = manager
        self.loop = loop

    def datagram_received(self, data, addr):
        # processa um datagrama de heartbeat recebido
        text = data.decode("utf-8", errors="ignore").strip()
        if not text.startswith("ALIVE:"):
            # formato invalido, ignora
            return
        agent_id = text[len("ALIVE:"):]
        if not agent_id:
            return
        # atualiza last_seen e se voltou a ficar online notifica dashboard
        changed = self.registry.touch(agent_id)
        if changed:
            agent = self.registry.get(agent_id)
            self.loop.create_task(self.manager.broadcast(frames.status_frame(agent)))


async def listen_udp_heartbeats(registry, manager):
    # abre o socket udp e retorna o transport para encerramento posterior
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: HeartbeatProtocol(registry, manager, loop),
        local_addr=(config.UDP_HOST, config.UDP_PORT),
    )
    return transport, protocol
