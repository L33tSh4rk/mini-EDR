# coletor de arquivos: observa mudancas no fs via watchdog (thread propria)

import asyncio
import os

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from agent.core import buffer, config, events


class _Handler(FileSystemEventHandler):
    # ponte entre os callbacks do watchdog (thread) e a asyncio.queue

    def __init__(self, state, queue, loop):
        self.state = state
        self.queue = queue
        self.loop = loop

    def _emit(self, file_path, action):
        # injeta o evento na queue de forma thread-safe (dropa com log se cheia)
        event = events.file_event(self.state.agent_id, file_path, action)
        self.loop.call_soon_threadsafe(buffer.enqueue, self.queue, event)

    def on_created(self, event):
        # arquivo criado
        if not event.is_directory:
            self._emit(event.src_path, "created")

    def on_modified(self, event):
        # arquivo modificado
        if not event.is_directory:
            self._emit(event.src_path, "modified")

    def on_deleted(self, event):
        # arquivo removido
        if not event.is_directory:
            self._emit(event.src_path, "deleted")


async def collect_files(state, queue):
    # inicia observer do watchdog e mantem vivo dentro do loop (async)
    loop = asyncio.get_running_loop()
    handler = _Handler(state, queue, loop)
    observer = Observer()
    # agenda observacao recursiva de cada caminho existente
    for path in config.WATCH_PATHS:
        if os.path.isdir(path):
            observer.schedule(handler, path, recursive=True)
    observer.start()
    try:
        # dorme indefinidamente enquanto o observer trabalha em thread separada
        while True:
            await asyncio.sleep(3600)
    finally:
        # para o observer no encerramento
        observer.stop()
        observer.join()
