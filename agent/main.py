# entrypoint do agente: enrollment e orquestracao dos loops assincronos

import asyncio

import redis.asyncio as aioredis

from agent.core import config
from agent.core.state import build_state
from agent.collectors.process_collector import collect_processes
from agent.collectors.file_collector import collect_files
from agent.network.enrollment import enroll_agent, periodic_reenroll
from agent.network.heartbeat import send_heartbeat
from agent.network.publisher import send_events_batch
from agent.network.commands import listen_commands
from agent.network import actions


async def connection_watchdog(state):
    # mecanismo de emergencia: auto-isola se perder o redis por mais de 20s
    while True:
        await asyncio.sleep(1)
        if not state.isolated and state.seconds_since_redis() > config.REDIS_TIMEOUT:
            print("[watchdog] redis inacessivel >20s, isolando host")
            await actions.execute_isolation(state)


async def _supervise(name, factory):
    # mantem uma task viva: re-inicia em caso de excecao inesperada
    # garante que uma falha isolada nao derrube o agente inteiro (gather)
    while True:
        try:
            await factory()
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[agent] task '{name}' caiu ({exc!r}); reiniciando em 2s")
            await asyncio.sleep(2)


async def main():
    # monta estado, registra agente e dispara todos os loops concorrentes
    state = build_state()
    print(f"[agent] iniciando agente {state.agent_id} ({state.hostname})")

    # enrollment bloqueia ate o servidor confirmar registro
    await enroll_agent(state)

    # buffer local de eventos com limite (backpressure; dropa quando cheio)
    queue = asyncio.Queue(maxsize=config.EVENT_QUEUE_MAX)

    # cliente redis assincrono usado por publisher e listener de comandos
    client = aioredis.Redis(
        host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True
    )

    # cada loop roda sob supervisao: falha isolada reinicia, nao mata o agente
    await asyncio.gather(
        _supervise("processes", lambda: collect_processes(state, queue)),
        _supervise("files", lambda: collect_files(state, queue)),
        _supervise("publisher", lambda: send_events_batch(state, queue, client)),
        _supervise("heartbeat", lambda: send_heartbeat(state)),
        _supervise("commands", lambda: listen_commands(state, client)),
        _supervise("watchdog", lambda: connection_watchdog(state)),
        _supervise("reenroll", lambda: periodic_reenroll(state)),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # encerramento limpo via ctrl+c
        print("\n[agent] encerrado")
