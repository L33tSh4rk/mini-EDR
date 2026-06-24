# coletor de processos: detecta processos novos via polling do psutil

import asyncio

import psutil

from agent.core import buffer, config, events


def _snapshot():
    # captura mapa pid -> info dos processos atuais (chamada sincrona do psutil)
    snap = {}
    for proc in psutil.process_iter(["pid", "name", "cmdline", "username"]):
        try:
            info = proc.info
            snap[info["pid"]] = {
                "process_name": info.get("name") or "",
                "cmdline": " ".join(info.get("cmdline") or []),
                "user": info.get("username") or "",
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # processo morreu ou sem permissao durante a leitura
            continue
    return snap


async def collect_processes(state, queue):
    # loop infinito que enfileira eventos de processos recem-criados
    loop = asyncio.get_running_loop()
    # snapshot inicial serve de baseline para nao alertar tudo no boot
    known = await loop.run_in_executor(None, _snapshot)
    while True:
        await asyncio.sleep(config.PROC_POLL_INTERVAL)
        try:
            # roda a leitura psutil fora do event loop
            current = await loop.run_in_executor(None, _snapshot)
        except Exception as exc:
            # falha transitoria no psutil nao pode derrubar o coletor
            print(f"[proc] falha no snapshot ({exc!r})")
            continue
        # pids presentes
        for pid in current.keys() - known.keys():
            info = current[pid]
            event = events.process_event(
                state.agent_id, pid, info["process_name"], info["cmdline"], info["user"]
            )
            # enfileira sem bloquear (dropa com log se fila estiver cheia)
            buffer.enqueue(queue, event)
        known = current
