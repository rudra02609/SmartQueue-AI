"""
WebSocket Connection Manager
Real-time updates for queue positions and token status

SAVE THIS FILE AS: app/services/websocket_manager.py
"""
from fastapi import WebSocket
from typing import Dict
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total: {len(self.active_connections)}")
        await self.send_personal_message({"type": "connection", "message": "Connected to SmartQueue AI", "client_id": client_id}, client_id)
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected. Remaining: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                print(f"Error sending to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: str):
        disconnected = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_json(self, message: dict):
        disconnected = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)
    
    def send_update(self, client_id: str, data: dict):
        if client_id in self.active_connections:
            asyncio.create_task(self.send_personal_message(data, client_id))
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)
    
    def is_connected(self, client_id: str) -> bool:
        return client_id in self.active_connections

manager = ConnectionManager()

async def notify_token_update(user_id: str, token_data: dict):
    message = {"type": "token_update", "data": token_data, "timestamp": str(asyncio.get_event_loop().time())}
    await manager.send_personal_message(message, str(user_id))

async def notify_position_change(user_id: str, new_position: int, estimated_wait: int):
    message = {"type": "position_update", "position": new_position, "estimated_wait_time": estimated_wait, "message": f"You are now #{new_position} in the queue"}
    await manager.send_personal_message(message, str(user_id))

async def notify_turn_alert(user_id: str, token_number: str):
    message = {"type": "turn_alert", "token_number": token_number, "message": "It's your turn! Please proceed to the counter.", "priority": "high"}
    await manager.send_personal_message(message, str(user_id))
