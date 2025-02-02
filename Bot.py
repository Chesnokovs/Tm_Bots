import logging
import asyncio
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram-токен бота (замените, если необходимо)
telegram_token = "1877732774:AAEPzLtdR7J3iWJEzNdSaZhzStjRNynMg1g"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start: приветствие пользователя."""
    await update.message.reply_text(
        "Привет! Я бот, который показывает текущую стоимость акций NVIDIA и прогноз их цены.\n\n"
        "Доступные команды:\n"
        "/nvda - текущая цена акций NVIDIA\n"
        "/forecast - прогноз цены акций NVIDIA\n"
        "/help - помощь по командам"
    )

def get_stock_price() -> str:
    """
    Получает текущую стоимость акций NVIDIA с помощью yfinance.
    Возвращает строку с ценой или сообщение об ошибке.
    """
    try:
        ticker = yf.Ticker("NVDA")
        # Получаем исторические данные за один торговый день
        data = ticker.history(period="1d")
        if not data.empty:
            # Берем последнюю цену закрытия
            price = data['Close'].iloc[-1]
            return f"Текущая цена акций NVIDIA: {price:.2f} USD"
        else:
            return "Не удалось получить цену акций NVIDIA."
    except Exception as e:
        logger.error(f"Ошибка при получении цены акций: {e}")
        return f"Ошибка при получении цены акций NVIDIA: {e}"

def get_stock_forecast() -> str:
    """
    Получает прогноз стоимости акций NVIDIA на основе двух источников:
    
    1. **Источник 1 (Yahoo Finance):** Аналитические данные (целевые цены).
    2. **Источник 2 (30-дневная скользящая средняя):** Среднее значение цены закрытия за последние 30 дней.
    
    Возвращает строку с прогнозом или сообщение об ошибке.
    """
    try:
        ticker = yf.Ticker("NVDA")
        forecast_msg = "Прогноз стоимости акций NVIDIA:\n\n"
        
        # Источник 1: данные из Yahoo Finance (если доступны)
        info = ticker.info
        target_mean = info.get("targetMeanPrice")
        target_low = info.get("targetLowPrice")
        target_high = info.get("targetHighPrice")
        if target_mean is not None:
            forecast_msg += f"Источник 1 (Yahoo Finance):\n" \
                            f"  Средняя целевая цена: {target_mean:.2f} USD"
            if target_low is not None and target_high is not None:
                forecast_msg += f" (диапазон: {target_low:.2f} - {target_high:.2f} USD).\n\n"
            else:
                forecast_msg += ".\n\n"
        else:
            forecast_msg += "Источник 1 (Yahoo Finance): Данные недоступны.\n\n"
        
        # Источник 2: 30-дневная скользящая средняя
        # Используем период "1mo" с интервалом "1d" для получения дневных данных за месяц.
        data_30 = ticker.history(period="1mo", interval="1d")
        if not data_30.empty:
            sma30 = data_30['Close'].mean()
            forecast_msg += f"Источник 2 (30-дневная скользящая средняя):\n" \
                            f"  {sma30:.2f} USD."
        else:
            forecast_msg += "Источник 2 (30-дневная скользящая средняя): Данные недоступны."
        
        return forecast_msg
    except Exception as e:
        logger.error(f"Ошибка при получении прогноза: {e}")
        return f"Ошибка при получении прогноза: {e}"

async def nvda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /nvda: отправка текущей цены акций NVIDIA."""
    loop = asyncio.get_running_loop()
    stock_price = await loop.run_in_executor(None, get_stock_price)
    await update.message.reply_text(stock_price)

async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /forecast: отправка прогноза цены акций NVIDIA."""
    loop = asyncio.get_running_loop()
    forecast_text = await loop.run_in_executor(None, get_stock_forecast)
    await update.message.reply_text(forecast_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help: вывод справки по командам."""
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - начать работу с ботом\n"
        "/nvda - показать текущую цену акций NVIDIA\n"
        "/forecast - показать прогноз цены акций NVIDIA"
    )

def main():
    # Создаем приложение с помощью билдера и передаем Telegram-токен
    application = Application.builder().token(telegram_token).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("nvda", nvda))
    application.add_handler(CommandHandler("forecast", forecast))
    application.add_handler(CommandHandler("help", help_command))

    # Запускаем бота (блокирующий вызов)
    application.run_polling()

if __name__ == '__main__':
    main()
