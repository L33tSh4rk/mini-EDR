# buffer local de eventos com descarte logado quando cheio (backpressure)

import asyncio


def enqueue(queue, event):
    # tenta enfileirar sem bloquear e dropa com log se fila estiver cheia
    try:
        queue.put_nowait(event)
        return True
    except asyncio.QueueFull:
        # evita crescimento ilimitado de memoria com redis offline
        print("[buffer] fila cheia, evento descartado")
        return False
