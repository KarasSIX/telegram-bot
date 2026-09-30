import os
import random
import time
import threading
from datetime import datetime
import telebot
from telebot import types
from dotenv import load_dotenv
from predictions import PREDICTIONS

# Завантажуємо секрети з файлу .env
load_dotenv()

# Зчитуємо токен безпечно із системної змінної
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Помилка: змінну BOT_TOKEN не знайдено! Перевірте наявність файлу .env")

bot = telebot.TeleBot(BOT_TOKEN)

# Добірка милих і затишних GIF з котиками та собачками
PREDICTION_GIFS = [
    # Котики
    "https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif",       # Котик медитує / спокій
    "https://media.giphy.com/media/ICOgUNjpvO0PC/giphy.gif",       # Котик махає лапкою
    "https://media.giphy.com/media/vFKqnCdLPNOKc/giphy.gif",       # Кумедний кіт
    "https://media.giphy.com/media/mlvseq9yvZhba/giphy.gif",       # Котик затишно чілить
    "https://media.giphy.com/media/MDJ9IbxxvDUQM/giphy.gif",       # Милий кіт із сердечками
    "https://media.giphy.com/media/7NoNw427MOGUs/giphy.gif",       # Котик солодко потягується
    
    # Песики
    "https://media.giphy.com/media/mCRJDo24UvJMA/giphy.gif",       # Коргі біжить
    "https://media.giphy.com/media/bbshzgyFQDqPHXBo4c/giphy.gif",  # Щасливий песик усміхається
    "https://media.giphy.com/media/4Zo41lhzKt6iZ8xff9/giphy.gif",  # Пухнастик дрімає в теплі
    "https://media.giphy.com/media/3oD3YQjT2cSZTWZAbm/giphy.gif",  # Песик у шапочці
    "https://media.giphy.com/media/13CoXDiaCcCoyk/giphy.gif",      # Радісне цуценя
    "https://media.giphy.com/media/26AHONQ79FdWZhAI0/giphy.gif"   # Чарівний космічний вайб
]

LUCKY_COLORS = [
    "Смарагдовий", "Глибокий синій", "Золотистий", "Лавандовий", 
    "Теплий бурштиновий", "Неоновий м'ятний", "Оксамитовий чорний", "Кораловий"
]

# Сховища в пам'яті
user_predictions = {}
subscribers = set()  # Список user_id, які увімкнули ранкові сповіщення
likes_counter = {}   # message_id -> кількість лайків

def get_next_prediction(user_id):
    """Повертає наступне унікальне передбачення без повторень."""
    if user_id not in user_predictions or not user_predictions[user_id]:
        shuffled = PREDICTIONS.copy()
        random.shuffle(shuffled)
        user_predictions[user_id] = shuffled
    return user_predictions[user_id].pop()

def generate_prediction_card(user_id):
    """Генерує текст передбачення, бонуси дня та випадкову GIF."""
    prediction = get_next_prediction(user_id)
    lucky_num = random.randint(1, 99)
    lucky_color = random.choice(LUCKY_COLORS)
    energy = random.randint(75, 100)
    gif_url = random.choice(PREDICTION_GIFS)

    caption = (
        "✨ <b>ВАШЕ ПЕРЕДБАЧЕННЯ</b> ✨\n\n"
        f"<blockquote>«{prediction}»</blockquote>\n\n"
        "🐾 <b>Вайб сьогоднішнього дня:</b>\n"
        f"• 🍀 Щасливе число: <b>{lucky_num}</b>\n"
        f"• 🎨 Колір удачі: <b>{lucky_color}</b>\n"
        f"• ⚡ Рівень енергії: <b>{energy}%</b>\n\n"
        "🌿 <i>Гарного дня та чудового настрою!</i>"
    )
    return gif_url, caption

def get_inline_keyboard(likes=0):
    """Інлайн-кнопки під карткою з анімацією."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_next = types.InlineKeyboardButton("🔄 Ще одне", callback_data="next_prediction")
    btn_like = types.InlineKeyboardButton(f"❤️ {likes}", callback_data="like")
    btn_share = types.InlineKeyboardButton("📤 Поділитися", switch_inline_query="Отримай своє миле передбачення тут! ✨")
    markup.add(btn_next, btn_like)
    markup.add(btn_share)
    return markup

def get_main_keyboard(user_id):
    """Нижня постійна клавіатура."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_pred = types.KeyboardButton("🔮 Отримати передбачення")
    
    notify_text = "🔕 Вимкнути нагадування" if user_id in subscribers else "⏰ Нагадувати щоранку (09:00)"
    btn_notify = types.KeyboardButton(notify_text)
    btn_help = types.KeyboardButton("ℹ️ Інформація")
    
    keyboard.add(btn_pred)
    keyboard.add(btn_notify, btn_help)
    return keyboard

# --- ФОНОВИЙ ПОТІК ДЛЯ ЩОДЕННОЇ РОЗСИЛКИ О 09:00 ---
def reminder_worker():
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute == 0:
            for uid in list(subscribers):
                try:
                    gif_url, caption = generate_prediction_card(uid)
                    bot.send_animation(
                        uid, 
                        animation=gif_url, 
                        caption="☀️ <b>Доброго ранку! Ваше передбачення на сьогодні:</b>\n\n" + caption,
                        parse_mode="HTML",
                        reply_markup=get_inline_keyboard()
                    )
                except Exception as e:
                    print(f"Помилка надсилання нагадування для {uid}: {e}")
            time.sleep(65)
        time.sleep(25)

threading.Thread(target=reminder_worker, daemon=True).start()

# --- ОБРОБНИКИ ТЕКСТОВИХ КОМАНД І КНОПОК ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    welcome_text = (
        f"Привіт, <b>{message.from_user.first_name}</b>! 👋\n\n"
        "Я бот щоденних передбачень. Отримуйте мудрі та милі знаки долі, "
        "дізнавайтеся щасливі кольори та заряджайтеся позитивом!\n\n"
        "Тисніть кнопку нижче, щоб отримати передбачення ✨"
    )
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard(user_id)
    )

@bot.message_handler(commands=['help'])
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Інформація")
def handle_help(message):
    help_text = (
        "<b>ℹ️ Можливості бота:</b>\n\n"
        "• <b>🔮 Отримати передбачення:</b> нове напуття з милим котиком або собачкою та бонусами дня.\n"
        "• <b>🔄 Кнопка під повідомленням:</b> генерує нове передбачення відразу в цьому ж повідомленні.\n"
        "• <b>⏰ Нагадування:</b> щоранку о 09:00 надсилає свіжу порцію мотивації на день.\n"
        "• Усі передбачення підбираються без повторень!"
    )
    bot.send_message(
        message.chat.id, 
        help_text, 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard(message.from_user.id)
    )

@bot.message_handler(func=lambda msg: msg.text in ["⏰ Нагадувати щоранку (09:00)", "🔕 Вимкнути нагадування"])
def toggle_subscription(message):
    user_id = message.from_user.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        bot.send_message(
            message.chat.id,
            "🔕 Щоденне нагадування вимкнено. Ви завжди можете ввімкнути його знову кнопкою в меню.",
            reply_markup=get_main_keyboard(user_id)
        )
    else:
        subscribers.add(user_id)
        bot.send_message(
            message.chat.id,
            "⏰ Чудово! Тепер щоранку о <b>09:00</b> я надсилатиму вам свіже передбачення.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(user_id)
        )

@bot.message_handler(func=lambda msg: msg.text == "🔮 Отримати передбачення")
def handle_prediction(message):
    user_id = message.from_user.id
    gif_url, caption = generate_prediction_card(user_id)
    
    sent = bot.send_animation(
        message.chat.id,
        animation=gif_url,
        caption=caption,
        parse_mode="HTML",
        reply_markup=get_inline_keyboard(likes=0)
    )
    likes_counter[sent.message_id] = 0

# --- ОБРОБНИКИ НА ТИСКАННЯ INLINE-КНОПОК ---

@bot.callback_query_handler(func=lambda call: call.data in ["next_prediction", "like"])
def handle_callback(call):
    user_id = call.from_user.id
    msg_id = call.message.message_id

    if call.data == "like":
        likes = likes_counter.get(msg_id, 0) + 1
        likes_counter[msg_id] = likes
        bot.answer_callback_query(call.id, text="Дякуємо за реакцію! ❤️")
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=msg_id,
            reply_markup=get_inline_keyboard(likes=likes)
        )

    elif call.data == "next_prediction":
        bot.answer_callback_query(call.id, text="Відкриваємо нове передбачення... 🔮")
        gif_url, new_caption = generate_prediction_card(user_id)
        likes_counter[msg_id] = 0
        
        media = types.InputMediaAnimation(media=gif_url, caption=new_caption, parse_mode="HTML")
        try:
            bot.edit_message_media(
                chat_id=call.message.chat.id,
                message_id=msg_id,
                media=media,
                reply_markup=get_inline_keyboard(likes=0)
            )
        except Exception:
            pass

print("🚀 Бот передбачень із милими гіфками та інтерактивними кнопками запущено!")
bot.infinity_polling()