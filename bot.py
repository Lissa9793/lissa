
import logging
import shelve
from gc import callbacks

from api import gpt, image
from enum import Enum
from telegram import ForceReply, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext,
                          CallbackQueryHandler)
from config import BOT_KEY1

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class ModelEnum(Enum):
    gpt_text = 1
    gpt_image = 2


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    user_name = user.full_name
    pandora = shelve.open("pandora")
    if str(user_id) not in pandora.keys():
        user_data = {
            "user_name": user_name,
            "subs": "Free",
            "tokens": 1,
            "model": ModelEnum.gpt_image.value
        }
        pandora[str(user_id)] = user_data
    await update.message.reply_text(f"Добро пожаловать в GPT бота! {pandora[str(user_id)]["user_name"]}")
    pandora.close()

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    pandora = shelve.open("pandora")
    subscription_type = pandora[str(user_id)]["subs"]
    tokens = pandora[str(user_id)]['tokens']
    name = pandora[str(user_id)]['user_name']
    profile_text = (
        f"Это ваш профиль. \n"
        f"Имя: {name}.\n"
        f"ID: {user_id}\n"
        f"Подписка: {subscription_type}\n\n"
        f"Лимиты: {tokens} token"
    )
    pandora.close()
    await update.message.reply_text(profile_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Для покупи токенов /store \n"
        "Для просмотра информации о вашем аккаунте /profile \n"
        "Для смены модели GPT /mode \n"
    )
    await update.message.reply_text(help_text)

async def store(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    await update.message.reply_text("Добро пожаловать в магазин! Сколько токенов хочешь купить?")
    pandora = shelve.open("pandora")
    pandora[user_id]["tokens"] = 20
    pandora[user_id]["subs"] = "VIP"
    pandora.close()

async def mode(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("GPT 3.5", callback_data="1")],
        [InlineKeyboardButton("Stable Diffusion",callback_data="2")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Тут можно сменить модель нейросетей", reply_markup=reply_markup)


async def button(update: Update, context: CallbackContext):
    pandora = shelve.open("pandora")
    query = update.callback_query
    mode_gpt = query.data
    user_id_chat = str(query.from_user.id)
    user_model = pandora[user_id_chat]
    user_model["model"] = int(mode_gpt)
    pandora[user_id_chat]["model"] = int(mode_gpt)
    selected_option = query.data
    pandora.close()

    new_keyboard = [
        [InlineKeyboardButton("GPT 3.5", callback_data="1")],
        [InlineKeyboardButton("Stable Diffusion", callback_data="2")]
    ]

    for row in new_keyboard:
        for button in row:
            if button.callback_data == selected_option:
                new_button = InlineKeyboardButton(f"☑️ {button.text}", callback_data=button.callback_data)
                row[row.index(button)] = new_button

    reply_markup = InlineKeyboardMarkup(new_keyboard)
    await query.edit_message_text(
        text="Тут можно сменить модель нейросетей",
        reply_markup=reply_markup
    )


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    pandora = shelve.open("pandora")
    tokens = pandora[user_id]["tokens"]
    gpt_model = pandora[user_id]["model"]
    if tokens > 0:
        if gpt_model == ModelEnum.gpt_text.value:
            message = update.message.text
            answer = gpt(message)
            await update.message.reply_text(answer)
        if gpt_model == ModelEnum.gpt_image.value:
            message = update.message.text
            answer = image(message)
            await update.message.reply_photo(
                photo=answer[0],
                caption=answer[1]
            )
    else:
        mess = "Пополните баланс токенов в /store"
        await update.message.reply_text(mess)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_KEY1).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mode", mode))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("store", store))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

