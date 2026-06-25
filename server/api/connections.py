# gerencia as conexoes websocket abertas com os dashboards

class ConnectionManager:
    # mantem o conjunto de dashboards conectados e faz broadcast de frames

    def __init__(self):
        # conjunto de websockets ativos
        self._active = set()

    async def connect(self, websocket):
        # aceita a conexao e registra o dashboard
        await websocket.accept()
        self._active.add(websocket)

    def disconnect(self, websocket):
        # remove o dashboard do conjunto ativo
        self._active.discard(websocket)

    async def broadcast(self, frame):
        # envia o frame json para todos os dashboards conectados
        dead = []
        for websocket in list(self._active):
            try:
                await websocket.send_json(frame)
            except Exception:
                # conexao quebrada, marca para remocao
                dead.append(websocket)
        for websocket in dead:
            self._active.discard(websocket)
