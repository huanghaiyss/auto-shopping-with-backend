import asyncio
import aiohttp
import websockets
import json

API_BASE = "http://127.0.0.1:8000"
AUTH_TOKEN = "mysecrettoken"
TARGET_SKUS = ["gift_001", "gift_002", "gift_003"]
QUANTITY = 1

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}"
}

async def fetch_gifts():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/gifts", headers=headers) as resp:
            return await resp.json()

async def purchase_gift(sku):
    async with aiohttp.ClientSession() as session:
        payload = {"sku": sku, "quantity": QUANTITY}
        async with session.post(f"{API_BASE}/purchase", json=payload, headers=headers) as resp:
            result = await resp.json()
            print(f"[purchase] Result for {sku}: {result}")

async def monitor_once():
    try:
        gifts = await fetch_gifts()
        for gift in gifts:
            if (
                gift["sku"] in TARGET_SKUS
                and gift["quantity"] >= QUANTITY
            ):
                print(f"[monitor] Initial match found for {gift['sku']}")
                await purchase_gift(gift["sku"])
                return
        print("[monitor] No initial match found")
    except Exception as e:
        print(f"[monitor] Error: {e}")

async def listen():
    url = "ws://127.0.0.1:8000/ws/gifts"
    async with websockets.connect(url) as ws:
        print("[socket] Connected to WebSocket")
        while True:
            try:
                data = await ws.recv()
                gift = json.loads(data)
                print(f"[socket] Received: {gift}")

                if (
                    gift.get("event") in ["gift_drop", "gift_update"]
                    and gift["sku"] in TARGET_SKUS
                    and gift["quantity"] >= QUANTITY
                ):
                    print(f"[socket] Match found for {gift['sku']}")
                    await purchase_gift(gift["sku"])
            except Exception as e:
                print(f"[socket] Error: {e}")
                break

async def main():
    await monitor_once()  # check just once at startup
    await listen()        # keep listening forever

if __name__ == "__main__":
    asyncio.run(main())
