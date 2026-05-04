class ConnectionManager:
    def __init__(self):
        self.active_connections = {}  # lead_id -> [ws connections]

    async def connect(self, lead_id: int, websocket):
        await websocket.accept()

        if lead_id not in self.active_connections:
            self.active_connections[lead_id] = []

        self.active_connections[lead_id].append(websocket)

    def disconnect(self, lead_id: int, websocket):
        if lead_id in self.active_connections:
            self.active_connections[lead_id].remove(websocket)

    async def send_to_lead(self, lead_id: int, message: dict):
        if lead_id in self.active_connections:
            for ws in self.active_connections[lead_id]:
                await ws.send_json(message)


manager = ConnectionManager()