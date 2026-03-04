import asyncio

import websockets


async def test():
    try:
        async with websockets.connect(
            "ws://localhost:8000/api/chat/ws", subprotocols=["jwt", "fake-token"]
        ) as ws:
            print("Connected to customer chat")
            await ws.close()
    except Exception as e:
        print(f"Customer Chat Failed: {e}")

    try:
        async with websockets.connect(
            "ws://localhost:8000/admin/api/chat/ws", subprotocols=["jwt", "fake-token"]
        ) as ws:
            print("Connected to admin chat")
            await ws.close()
    except Exception as e:
        print(f"Admin Chat Failed: {e}")


asyncio.run(test())
