import asyncio
import json

import websockets


WS_URL = "ws://127.0.0.1:8000/ws/tasks"


async def listen_tasks() -> None:
    print(f"Подключаюсь к {WS_URL} ...")
    async with websockets.connect(WS_URL) as ws:
        print("✅ Подключено к WebSocket /ws/tasks")

        async def sender():
            # Периодически шлём ping, чтобы соединение жило
            while True:
                try:
                    await ws.send("ping")
                except Exception as e:
                    print(f"[sender] ошибка при отправке ping: {e}")
                    break
                await asyncio.sleep(5)

        async def receiver():
            # Читаем все сообщения от сервера
            async for message in ws:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    print(f"[recv] сырой текст: {message}")
                    continue

                event = data.get("event")
                task_id = data.get("task_id")
                task = data.get("task")

                print("\n=== WebSocket событие ===")
                print(f"event:   {event}")
                print(f"task_id: {task_id}")
                if task:
                    print(f"title:   {task.get('title')}")
                    print(f"done:    {task.get('completed')}")
                print("==========================")

        await asyncio.gather(sender(), receiver())


def main() -> None:
    try:
        asyncio.run(listen_tasks())
    except KeyboardInterrupt:
        print("\nОтключение клиента...")


if __name__ == "__main__":
    main()
