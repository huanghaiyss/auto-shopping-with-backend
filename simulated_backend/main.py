from fastapi import FastAPI, Header, HTTPException, Depends,BackgroundTasks
from sqlmodel import Session, select
from models import Gift, PurchaseRequest, User
from database import engine, init_db
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json

app = FastAPI()
init_db()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
def get_session():
    with Session(engine) as session:
        yield session

def get_user(authorization: str = Header(...), session: Session = Depends(get_session)):
    token = authorization.replace("Bearer ", "")
    user = session.exec(select(User).where(User.token == token)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.websocket("/ws/gifts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Optional: keep-alive pings
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/admin/add_gift")
def add_new_gift(
    gift: Gift,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    existing = session.exec(select(Gift).where(Gift.sku == gift.sku)).first()

    if existing:
        # Merge quantities
        existing.quantity += gift.quantity
        session.add(existing)
        session.commit()

        background_tasks.add_task(manager.broadcast, {
            "event": "gift_update",
            "sku": existing.sku,
            "name": existing.name,
            "quantity": existing.quantity,
            "added": gift.quantity,
            "drop": False
        })
        return {
            "ok": True,
            "message": f"Existing gift updated. Added {gift.quantity} more units.",
            "sku": existing.sku,
            "quantity": existing.quantity
        }
    else:
        session.add(gift)
        session.commit()

        background_tasks.add_task(manager.broadcast, {
            "event": "gift_drop",
            "sku": gift.sku,
            "name": gift.name,
            "quantity": gift.quantity,
            "drop": True
        })

        return {
            "ok": True,
            "message": "New gift added.",
            "sku": gift.sku,
            "quantity": gift.quantity
        }

@app.get("/gifts")
def get_gifts(session: Session = Depends(get_session)):
    return session.exec(select(Gift)).all()

@app.post("/purchase")
def purchase_gift(p: PurchaseRequest, user: User = Depends(get_user), session: Session = Depends(get_session)):
    gift = session.exec(select(Gift).where(Gift.sku == p.sku)).first()
    if not gift or gift.quantity < p.quantity:
        raise HTTPException(status_code=404, detail="Gift not available")

    cost = p.quantity * 1  # 1 star per gift
    if user.stars < cost:
        return {"success": False, "error": "Insufficient stars"}

    gift.quantity -= p.quantity
    user.stars -= cost
    session.add(gift)
    session.add(user)
    session.commit()

    return {"success": True, "order_id": f"ORD-{p.sku.upper()}", "remaining_stars": user.stars}
