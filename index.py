import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import asyncio
import random

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Вставьте сюда свой токен
TOKEN = '7329302158:AAFiDOSMwf4ATGA2-FidUUtqoE19ERMj4bA'

# Глобальная переменная для хранения предыдущего количества подписчиков
previous_subscriber_count = 0

# Функция для получения информации о канале
async def get_channel_info(channel_id):
    if channel_id.startswith('@'):
        chat_id = channel_id
    else:
        # Проверяем, является ли channel_id ссылкой на канал и извлекаем название канала
        if channel_id.startswith('https://t.me/'):
            channel_id = channel_id.replace('https://t.me/', '')
        elif channel_id.startswith('t.me/'):
            channel_id = channel_id.replace('t.me/', '')
        chat_id = f'@{channel_id}'
        
    # Генерируем случайное число от 0 до 1000 и добавляем его к URL как параметр запроса
    random_value = random.randint(0, 1000)
    url = f'https://api.telegram.org/bot{TOKEN}/getChatMembersCount?chat_id={chat_id}&random={random_value}'
    
    # Отладочная информация
    logger.info(f"Запрос к API Telegram: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверяем статус ответа
        
        # Отладочная информация
        logger.info(f"Ответ от API Telegram: {response.text}")
        
        data = response.json()
        if data['ok']:
            return data['result']
        else:
            logger.error(f"Error fetching channel info: {data['description']}")
            return data['description']  # Возвращаем описание ошибки
    except Exception as e:
        logger.error(f"Error fetching channel info: {str(e)}")
        return str(e)  # Возвращаем текст ошибки

# Функция для отслеживания изменений в количестве подписчиков
async def track_subscriber_changes(channel_id):
    global previous_subscriber_count
    
    while True:
        current_subscriber_count = await get_channel_info(channel_id)
        
        if isinstance(current_subscriber_count, int):
            # Если текущее количество подписчиков меньше предыдущего, значит кто-то отписался
            if current_subscriber_count < previous_subscriber_count:
                diff = previous_subscriber_count - current_subscriber_count
                logger.info(f"Отписалось {diff} человек(а)")
            # Если текущее количество подписчиков больше предыдущего, значит кто-то подписался
            elif current_subscriber_count > previous_subscriber_count:
                diff = current_subscriber_count - previous_subscriber_count
                logger.info(f"Подписалось {diff} человек(а)")
            
            # Обновляем значение previous_subscriber_count
            previous_subscriber_count = current_subscriber_count
        else:
            logger.error(f"Ошибка при получении информации о канале: {current_subscriber_count}")
        
        # Ждем некоторое время перед следующей проверкой
        await asyncio.sleep(5)  #

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправь мне команду /check <channel_id>, чтобы узнать количество подписчиков.')

# Обработчик команды /check
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('Пожалуйста, укажи идентификатор канала.')
        return
    
    channel_id = context.args[0]
    
    # Выводим приветственное сообщение в консоль
    logger.info(f"Привет! Запрошена информация о канале {channel_id}.")
    
    result = await get_channel_info(channel_id)
    
    if isinstance(result, int):  # Проверка, является ли результат числом
        await update.message.reply_text(f'Количество подписчиков в канале @{channel_id}: {result}')
        await track_subscriber_changes(channel_id)
    else:
        await update.message.reply_text(f'Не удалось получить информацию о канале @{channel_id}. Ошибка: {result}
        )
def main():
    # Создаем приложение и передаем ему токен бота.
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()