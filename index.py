import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import requests
import asyncio
import random
from datetime import datetime, timedelta

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Вставьте сюда свой токен
TOKEN = '7329302158:AAFiDOSMwf4ATGA2-FidUUtqoE19ERMj4bA'

# Глобальные переменные для хранения данных
previous_subscriber_count = {}
channels = {}
subscriber_data = {}

# Функция для получения информации о канале
async def get_channel_info(channel_id):
    if channel_id.startswith('@'):
        chat_id = channel_id
    else:
        if channel_id.startswith('https://t.me/'):
            channel_id = channel_id.replace('https://t.me/', '')
        elif channel_id.startswith('t.me/'):
            channel_id = channel_id.replace('t.me/', '')
        chat_id = f'@{channel_id}'
        
    random_value = random.randint(0, 1000)
    url = f'https://api.telegram.org/bot{TOKEN}/getChatMembersCount?chat_id={chat_id}&random={random_value}'
    logger.info(f"Запрос к API Telegram: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        logger.info(f"Ответ от API Telegram: {response.text}")
        
        data = response.json()
        if data['ok']:
            return data['result']
        else:
            logger.error(f"Error fetching channel info: {data['description']}")
            return data['description']
    except Exception as e:
        logger.error(f"Error fetching channel info: {str(e)}")
        return str(e)

# Функция для отслеживания изменений в количестве подписчиков
async def track_subscriber_changes(channel_id):
    global previous_subscriber_count
    
    while True:
        current_subscriber_count = await get_channel_info(channel_id)
        
        if isinstance(current_subscriber_count, int):
            if channel_id not in previous_subscriber_count:
                previous_subscriber_count[channel_id] = current_subscriber_count
            
            if current_subscriber_count < previous_subscriber_count[channel_id]:
                diff = previous_subscriber_count[channel_id] - current_subscriber_count
                logger.info(f"Отписалось {diff} человек(а)")
            elif current_subscriber_count > previous_subscriber_count[channel_id]:
                diff = current_subscriber_count - previous_subscriber_count[channel_id]
                logger.info(f"Подписалось {diff} человек(а)")
            
            previous_subscriber_count[channel_id] = current_subscriber_count
        else:
            logger.error(f"Ошибка при получении информации о канале: {current_subscriber_count}")
        
        await asyncio.sleep(60)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправь мне команду /add <channel_link>, чтобы добавить канал.')

# Обработчик команды /add для добавления канала
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) == 0:
            await update.message.reply_text('Пожалуйста, укажите ссылку на канал.')
            return

        channel_link = context.args[0]
        channel_id = channel_link.replace('https://t.me/', '').replace('t.me/', '')
        channels[channel_id] = channel_link

        logger.info(f'Канал {channel_link} добавлен. Текущий список каналов: {channels}')
        
        await update.message.reply_text(f'Канал {channel_link} добавлен.')

        # Запустите track_subscriber_changes в отдельном потоке
        asyncio.create_task(track_subscriber_changes(channel_id))
    except Exception as e:
        logger.error(f"An error occurred in add: {e}")

# Обработчик команды /list для вывода списка каналов
async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        logger.info(f"Запрос на список каналов. Текущий список каналов: {channels}")
        
        if not channels:
            await update.message.reply_text('Нет добавленных каналов.')
            return

        keyboard = [[InlineKeyboardButton(channel_id, callback_data=channel_id)] for channel_id in channels]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выбери канал:', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"An error occurred in list_channels: {e}")

# Обработчик для выбора канала
async def select_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    channel_id = query.data
    context.user_data['selected_channel'] = channel_id
    
    await query.edit_message_text(text=f'Канал {channel_id} выбран. Теперь выбери дату и время.')
    await query.message.reply_text('Отправь дату и время в формате "YYYY-MM-DD HH:MM:SS - YYYY-MM-DD HH:MM:SS".')

# Обработчик для выбора даты и времени
async def select_date_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'selected_channel' not in context.user_data:
        await update.message.reply_text('Сначала выбери канал командой /list.')
        return

    date_time_range = update.message.text
    try:
        start_str, end_str = date_time_range.split(' - ')
        start_date = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')

        # Замените это на реальную функцию получения подписчиков
        subscribers = [
            {"name": "User1", "username": "user1", "join_date": start_date + timedelta(hours=1), "status": "joined"},
            {"name": "User2", "username": "user2", "join_date": start_date + timedelta(hours=2), "status": "left"},
        ]

        filtered_subscribers = [
            s for s in subscribers if start_date <= s["join_date"] <= end_date
        ]

        response = f"Подписчики с {start_str} до {end_str}:\n"
        response += "\n".join([f'{s["name"]} (@{s["username"]}) - {s["join_date"]} - {s["status"]}' for s in filtered_subscribers])

        await update.message.reply_text(response)
    except ValueError:
        await update.message.reply_text('Неверный формат. Используйте "YYYY-MM-DD HH:MM:SS - YYYY-MM-DD HH:MM:SS".')

# Основная функция
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("list", list_channels))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, select_date_time))
    application.add_handler(CallbackQueryHandler(select_channel))

    application.run_polling()

if __name__ == '__main__':
    main()
