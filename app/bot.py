import asyncio
import json
from datetime import datetime

from loguru import logger
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.dependencies import config, idu_llm_api_client

bot = AsyncTeleBot(config.get("TG_TOKEN"), parse_mode=None)
cnt = 0


users_settings = {}


freq_limit_amount_per_second = 4


commands = [
    BotCommand("start", "Запустить бота"),
    BotCommand("menu", "Открыть главное меню"),
]


async def show_categories(message):

    markup = InlineKeyboardMarkup(row_width=1)
    index_list = await idu_llm_api_client.get_available_indexes()
    for index in index_list:
        markup.add(
            InlineKeyboardButton(
                index,
                callback_data=index,
            )
        )
    markup.add(InlineKeyboardButton("← Назад", callback_data="back_main"))
    await bot.edit_message_text(
        "Выберите стадию:",
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=markup,
    )


async def choose_index(chat_id, index_name: str):

    users_settings[chat_id] = index_name
    await bot.send_message(
        chat_id,
        f'В качестве стадии выбрана "{index_name}"',
    )


@bot.message_handler(commands=["menu"])
async def show_menu(message):

    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("Стадии", callback_data="phase"),
    )

    await bot.send_message(
        message.chat.id, "📱 *Главное меню*", parse_mode="Markdown", reply_markup=markup
    )


@bot.message_handler(commands=["start"])
async def send_welcome(message):
    await bot.set_my_commands(commands)
    await bot.reply_to(
        message,
        """Привет! Я ассистент ИДУ ИТМО! Вы можете задать мне любой вопрос по документам.""",
    )

    markup = InlineKeyboardMarkup(row_width=2)

    index_button = InlineKeyboardButton("Выбрать стадию", callback_data="phase")
    markup.add(index_button)
    await bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    index_list = await idu_llm_api_client.get_available_indexes()
    if call.data == "phase":
        await show_categories(call.message)
    elif call.data == "main":
        await show_menu(call.message)
    elif call.data in index_list:
        await choose_index(call.message.chat.id, call.data)
    elif call.data == "back_main":
        await send_welcome(call.message)


@bot.message_handler(func=lambda m: True)
async def echo(message: Message):
    global cnt
    cnt += 1
    print(
        f"{datetime.now().strftime('%d.%m %H:%M')} from {message.from_user.username} accepted: {message.text}"
    )
    if (index_name := users_settings.get(message.chat.id)) is None:
        await bot.reply_to(message, "Вы не выбрали стадию, сначала выберите стадию")
        return
    response_message: Message | None = None
    next_message = ""
    last_response_timestamp = datetime.now().timestamp() * 1000

    errors = {}

    try:
        async for chunk in idu_llm_api_client.get_response_from_llm(
            index_name, message.text
        ):
            if chunk.get("type") == "status":
                text_chunk = "\n" + chunk.get("chunk") + "...\n"
            elif chunk.get("type") == "text":
                text_chunk = chunk.get("chunk")
            else:
                text_chunk = chunk
                error_message = (
                    "Unknown chunk type {}, please contact {} for help.".format(
                        json.dumps(text_chunk), config.get("SUPPORT_CONTACT")
                    )
                )
                await bot.reply_to(message, error_message)
                raise Exception(
                    "Unknown chunk type received: {}".format(chunk.get("type"))
                )
            if response_message is None:
                response_message = await bot.reply_to(message, text_chunk)
                next_message = response_message.text
                last_response_timestamp = datetime.now().timestamp() * 1000
                continue
            next_message += text_chunk
            cur_ts = datetime.now().timestamp() * 1000
            cur_freq = 1000 / freq_limit_amount_per_second * max(1, cnt)
            if cur_ts - last_response_timestamp > cur_freq:
                try:
                    response_message = await bot.edit_message_text(
                        next_message,
                        chat_id=response_message.chat.id,
                        message_id=response_message.message_id,
                    )
                    last_response_timestamp = cur_ts

                except ApiTelegramException as e:
                    errors.setdefault(
                        e.error_code,
                        {"cnt": 0, "descriptions": set()},
                    )
                    errors[e.error_code]["cnt"] += 1
                    errors[e.error_code]["descriptions"].add(e.description)
                    continue

    except Exception as e:
        logger.exception("LLM websocket error", exc_info=e)
        await bot.reply_to(message, "cant connect to llm")
        cnt -= 1
        return

    if response_message:
        try:
            await bot.edit_message_text(
                next_message,
                chat_id=response_message.chat.id,
                message_id=response_message.message_id,
            )
        except ApiTelegramException as e:
            errors.setdefault(
                e.error_code,
                {"cnt": 0, "descriptions": set()},
            )
            errors[e.error_code]["cnt"] += 1
            errors[e.error_code]["descriptions"].add(e.description)

    if next_message:
        error_msg = ""
        for k, v in errors.items():
            error_msg += (
                f" - {k}: количество {v['cnt']}, "
                f"описания: {list(v['descriptions'])}\n"
            )

        text = (
            f"Сообщение от {message.chat.username}: {message.text}\n\n"
            f"Ответ: {next_message}"
        )
        logger.info(text)

        if error_msg:
            text += f"\n\nОшибки во время ответа:\n{error_msg}"

    cnt -= 1


async def main():

    logger.info("Starting bot instance")
    await bot.polling()
    logger.info("Bot instance is shutting down")


if __name__ == "__main__":
    asyncio.run(main())
