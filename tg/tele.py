# /// script
# dependencies = [
#     "quart",
#     "telethon",
# ]
# ///

import re
import asyncio
from quart import Quart, jsonify, request
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import ChannelInvalidError, ChannelPrivateError

# --- НАСТРОЙКИ ---
api_id = 'xxx'            # заменить id тут
api_hash = 'zxczxczxc'    # и тут
session_name = 'telegram_ha_session'

# --- Инициализация ---
app = Quart(__name__)

client = None 

def clean_message_text(text):
    if not text:
        return ""
    text_after_markdown = re.sub(r'\[([^\]]+)\]\(\S+\)', r'\1', text)
    cleaned_text = re.sub(r'https?://\S+|www\.\S+', '', text_after_markdown)
    return " ".join(cleaned_text.split())

@app.route('/get_messages', methods=['GET'])
async def get_telegram_messages():
    global client

    if not client:
        return jsonify({"error": "Telegram client not initialized"}), 500

    channel_name = request.args.get('channel')
    if not channel_name:
        return jsonify({"error": "Query parameter 'channel' is required"}), 400

    DEFAULT_LIMIT = 15
    try:
        message_limit = int(request.args.get('limit', DEFAULT_LIMIT))
        if not 1 <= message_limit <= 100:
            return jsonify({"error": "'limit' parameter must be between 1 and 100"}), 400
    except ValueError:
        return jsonify({"error": "Invalid 'limit' parameter. Must be an integer."}), 400
    
    print(f"Запрос: {message_limit} сообщений из {channel_name}")

    try:
        if not await client.is_user_authorized():
            return jsonify({"error": "Client not authorized."}), 401

        messages = await client.get_messages(channel_name, limit=message_limit)
        message_texts = []
        for msg in messages:
            if msg and msg.text:
                cleaned_text = clean_message_text(msg.text)
                if cleaned_text:
                    message_texts.append(cleaned_text)
        
        return jsonify({
            "channel": channel_name,
            "requested_limit": message_limit,
            "message_count": len(message_texts),
            "messages": message_texts
        })

    except (ValueError, ChannelInvalidError, ChannelPrivateError) as e:
        error_message = f"Cannot find or access channel '{channel_name}'. Error: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 404
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

@app.before_serving
async def startup():
    """
    Здесь мы находимся ВНУТРИ цикла событий Quart.
    Именно здесь нужно создавать боевой экземпляр клиента.
    """
    global client
    print("Создание клиента Telethon в цикле Quart...")
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("ОШИБКА: Клиент не авторизован! Перезапустите скрипт интерактивно.")
    else:
        me = await client.get_me()
        print(f"Клиент Telethon подключен как: {me.first_name}")

@app.after_serving
async def shutdown():
    global client
    if client:
        print("Отключение клиента Telethon...")
        await client.disconnect()
        print("Клиент Telethon отключен.")

if __name__ == '__main__':
    print("--- Проверка сессии Telegram ---")
    
    temp_client = TelegramClient(session_name, api_id, api_hash)
    temp_client.start()
    temp_client.disconnect()
    
    print("Сессия проверена/создана. Запуск веб-сервера...")
    

    app.run(host='0.0.0.0', port=5000)    # можно назначить другой порт

