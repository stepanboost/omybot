from telethon.sync import TelegramClient, events
import os
import requests

api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
channel_username = os.environ['CHANNEL_NAME']
make_webhook_url = os.environ['MAKE_WEBHOOK']

client = TelegramClient('session_lemonfortea', api_id, api_hash)

@client.on(events.NewMessage(chats=channel_username))
async def handler(event):
    message_text = event.message.message or ''
    payload = {
        "text": message_text
    }

    print(f"Получено сообщение из @{channel_username}:")
    print(message_text)

    try:
        requests.post(make_webhook_url, json=payload)
    except Exception as e:
        print("Ошибка при отправке в Make:", e)

print("Скрипт запущен. Слушаю канал @" + channel_username + "...")
client.start()
client.run_until_disconnected()
