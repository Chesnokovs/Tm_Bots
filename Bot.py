import logging
import asyncio
import requests
import yfinance as yf
import openai
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ключи и токены
telegram_token = "1877732774:AAEPzLtdR7J3iWJEzNdSaZhzStjRNynMg1g"
news_api_key = "d23c96fa85b5454c9a5fdf2dccf0b85e"
openai.api_key = "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"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие пользователя и перечень доступных команд."""
    await update.message.reply_text(
        "Привет! Я бот, который показывает информацию по акциям NVIDIA.\n\n"
        "Доступные команды:\n"
        "/price - показать текущую цену и прогноз цены акций NVIDIA\n"
        "/news - показать краткое резюме новостей по NVIDIA\n"
        "/help - помощь по командам"
    )

def get_stock_price() -> str:
    """Получает текущую стоимость акций NVIDIA с помощью yfinance."""
    try:
        ticker = yf.Ticker("NVDA")
        data = ticker.history(period="1d")
        if not data.empty:
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
      1. Данные Yahoo Finance (целевые цены)
      2. 30-дневная скользящая средняя цены закрытия
    """
    try:
        ticker = yf.Ticker("NVDA")
        forecast_msg = "Прогноз стоимости акций NVIDIA:\n\n"
        
        # Источник 1: данные из Yahoo Finance
        info = ticker.info
        target_mean = info.get("targetMeanPrice")
        target_low = info.get("targetLowPrice")
        target_high = info.get("targetHighPrice")
        if target_mean is not None:
            forecast_msg += f"Источник 1 (Yahoo Finance):\n  Средняя целевая цена: {target_mean:.2f} USD"
            if target_low is not None and target_high is not None:
                forecast_msg += f" (диапазон: {target_low:.2f} - {target_high:.2f} USD)."
            # Вычисляем дату: сегодня + 30 дней
            target_date = (datetime.utcnow() + timedelta(days=30)).strftime("%d.%m.%Y")
            forecast_msg += f"\nСредняя целевая цена рассчитана до: {target_date}\n\n"
        else:
            forecast_msg += "Источник 1 (Yahoo Finance): Данные недоступны.\n\n"
        
        # Источник 2: 30-дневная скользящая средняя (период 1mo, интервал 1d)
        data_30 = ticker.history(period="1mo", interval="1d")
        if not data_30.empty:
            sma30 = data_30['Close'].mean()
            forecast_msg += f"Источник 2 (30-дневная скользящая средняя):\n  {sma30:.2f} USD."
        else:
            forecast_msg += "Источник 2 (30-дневная скользящая средняя): Данные недоступны."
        
        return forecast_msg
    except Exception as e:
        logger.error(f"Ошибка при получении прогноза: {e}")
        return f"Ошибка при получении прогноза: {e}"

def get_combined_info() -> str:
    """
    Объединяет текущую цену и прогноз акций NVIDIA в один ответ.
    """
    price_info = get_stock_price()
    forecast_info = get_stock_forecast()
    combined = f"{price_info}\n\n{forecast_info}"
    return combined

def get_nvidia_news_raw() -> str:
    """
    Получает последние новости по NVIDIA из выбранных источников через endpoint "everything" NewsAPI.
    Ограничивает поиск доменами: reuters.com, cnbc.com, businessinsider.com, bloomberg.com, wsj.com, ft.com.
    Формирует текстовое описание новостей с заголовками, описаниями и ссылками за последние 2 недели.
    """
    try:
        # Вычисляем даты: "from" - две недели назад, "to" - текущая дата (UTC)
        to_date = datetime.utcnow().strftime('%Y-%m-%d')
        from_date = (datetime.utcnow() - timedelta(weeks=2)).strftime('%Y-%m-%d')
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "NVIDIA",
            "domains": "reuters.com,cnbc.com,businessinsider.com,bloomberg.com,wsj.com,ft.com",
            "language": "en",
            "sortBy": "publishedAt",
            "from": from_date,
            "to": to_date,
            "apiKey": news_api_key,
            "pageSize": 6  # Попытка получить по одной новости с каждого источника
        }
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("status") != "ok":
            return f"Ошибка при получении новостей: {data.get('message', 'Неизвестная ошибка')}"
        articles = data.get("articles", [])
        if not articles:
            return "Нет новостей по NVIDIA."
        
        news_text = ""
        for article in articles:
            source = article["source"]["name"]
            title = article["title"]
            description = article.get("description", "Описание отсутствует")
            url_article = article["url"]
            news_text += (f"Источник: {source}\n"
                          f"Заголовок: {title}\n"
                          f"Описание: {description}\n"
                          f"Ссылка: {url_article}\n\n")
        return news_text
    except Exception as e:
        logger.error(f"Ошибка при получении новостей: {e}")
        return f"Ошибка при получении новостей: {e}"

def summarize_news(news_text: str) -> str:
    """
    Передаёт текст новостей в OpenAI API (с использованием ChatCompletion.create)
    для получения краткого резюме, разбитого на 6 параграфов — по одному для каждого источника.
    Если текст слишком длинный, обрезает его до 1500 символов.
    Параметр max_tokens увеличен до 500.
    """
    try:
        max_length = 1500
        if len(news_text) > max_length:
            news_text = news_text[:max_length] + "\n...[текст обрезан]"

        prompt = (
            "Суммируй следующие новости по NVIDIA и дай краткое резюме. "
            "Разбей итоговое резюме на 6 параграфов, где каждый параграф соответствует одному из следующих источников:\n"
            "reuters.com, cnbc.com, businessinsider.com, bloomberg.com, wsj.com, ft.com.\n"
            "Если для какого-либо источника новостей нет, укажи, что новости отсутствуют.\n\n"
            f"{news_text}\n\n"
            "Резюме должно быть коротким, содержательным и структурированным по источникам."
        )
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты помощник по суммаризации новостей."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        summary = response["choices"][0]["message"]["content"].strip()
        return summary
    except Exception as e:
        logger.error(f"Ошибка при суммаризации новостей: {e}")
        return f"Ошибка при суммаризации новостей: {e}"

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработка команды /price:
    1. Получает текущую цену акций NVIDIA.
    2. Получает прогноз цены акций NVIDIA.
    3. Выводит объединённую информацию.
    """
    loop = asyncio.get_running_loop()
    combined_info = await loop.run_in_executor(None, get_combined_info)
    await update.message.reply_text(combined_info)

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработка команды /news:
    1. Получает новости по NVIDIA за последние 2 недели через NewsAPI.
    2. Передаёт полученный текст в OpenAI для суммаризации.
    3. Отправляет итоговое краткое резюме пользователю.
    """
    loop = asyncio.get_running_loop()
    raw_news = await loop.run_in_executor(None, get_nvidia_news_raw)
    if raw_news.startswith("Ошибка") or raw_news.startswith("Нет новостей"):
        await update.message.reply_text(raw_news)
        return
    summary = await loop.run_in_executor(None, summarize_news, raw_news)
    await update.message.reply_text(summary)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Вывод справки по командам."""
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - начать работу с ботом\n"
        "/price - показать текущую цену и прогноз акций NVIDIA\n"
        "/news - показать краткое резюме новостей по NVIDIA\n"
        "/help - помощь по командам"
    )

def main():
    """Создаёт и запускает Telegram-бота."""
    application = Application.builder().token(telegram_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("help", help_command))

    application.run_polling()

if __name__ == '__main__':
    main()
