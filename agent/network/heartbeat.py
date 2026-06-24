# heartbeat: envia datagrama udp periodico sinalizando vida ao servidor

import asyncio
import socket

from agent.core import config


async def send_heartbeat(state):
    # loop infinito que envia ALIVE:{agent_id} via udp ao servidor
    # socket udp nao mantem conexao, sobrevive ao isolamento (servidor liberado)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (config.SERVER_HOST, config.SERVER_UDP_PORT)
    message = f"ALIVE:{state.agent_id}".encode("utf-8")
    try:
        while True:
            try:
                # sendto e nao bloqueante para um unico datagrama
                sock.sendto(message, addr)
            except OSError as exc:
                # erro transitorio de rede (ex.: durante isolamento); loga e segue
                print(f"[heartbeat] falha no envio udp ({exc})")
            await asyncio.sleep(config.HEARTBEAT_INTERVAL)
    finally:
        # fecha o socket no encerramento
        sock.close()
