import os
from asyncio import run, sleep

import g4f.gui

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Filter, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError
from dotenv import load_dotenv

load_dotenv('.env')

bot = Bot(os.getenv('TOKEN'))
dp = Dispatcher()

help_text = """
<b>Для того чтобы начать</b> напишите /start.

<b>Для того чтобы сбросить диалог</b> напишите /clear.

<b>Для выбора языковой модели</b> напишите /menu.

<b>Для общения</b> напишите боту сообщение.

<b>Для общения в группе</b> напишите боту "@{} сообщение".

<b>Если бот не отвечает в течении 5 мин.</b> попробуйте написать ещё раз.

<b>Если бот завис</b>, то напишите /start. Если не сработало напишите:
{}
"""

# settings_file = open('settings.json', 'a+')
# src = settings_file.readline().strip().replace("'", '"')
# db = json.loads(src)
# print(db)
db = dict()
# settings_file.close()
#
#
# def save(settings_file_name: str = 'settings.json'):
#     settings_file = open(settings_file_name, 'w')
#     settings_file.write(f'{db}'.replace("'", '"'))
#     settings_file.close()


print(g4f.models._all_models)
supported_models = [
    'gpt-4', 'gpt-3.5-long',
    'gpt-3.5-turbo',
    'Auto'
]

# print(aiogram.__version__)
# from telebot import TeleBot, types

# for provider in g4f.Provider.__providers__:
#     if 'stream' in provider.params:
#         print(provider.__name__, 'true')

ADMINS = ["@Dmitrii_gr"]
MODERATORS = []

# ---------------------------------------------
g4f.debug.logging = False
g4f.debug.version_check = False


# Using automatic a provider for the given model
# Streamed completion
# ---------------------------------------------

class Is_Admin(Filter):
    def __init__(self, admins=ADMINS, moderators=MODERATORS) -> None:
        self.ADMINS = admins
        self.MODERATORS = moderators

    async def __call__(self, msg: types.Message) -> bool:
        if msg.from_user is not None:
            return (msg.from_user.id in self.ADMINS or
                    "@" + msg.from_user.username in self.ADMINS or

                    msg.from_user.id in self.MODERATORS or
                    "@" + msg.from_user.username in self.MODERATORS)


class Command_chat(Filter):
    def __init__(self, commands) -> None:
        self.commands = commands
        self.username = 'ChatGPT_g4f_bot'
        self.commands_chat = [command + f'@{self.username}' for command in commands]

    async def __call__(self, msg: types.Message) -> bool:
        if msg.chat.type == 'private':
            return await Command(commands=self.commands).__call__(msg, bot)
        if msg.chat.type != 'private':
            return await Command(commands=self.commands_chat).__call__(msg, bot)


async def username_to_id(username: str):
    if username.isnumeric():
        return username
    for id, value in db.items():
        if f"@{value['info'].username}" == username:
            return id
    return False


async def send_moderators(text):
    for chat_id in MODERATORS:
        id = await username_to_id(chat_id)
        if id:
            await bot.send_message(chat_id=id, text=text, parse_mode='html')
        else:
            MODERATORS.remove(chat_id)
            db[int(id)]["is_subscribed"] = False
            await send_moderators(
                f'При очередной отправки модератору "<b>{chat_id}</b>", произошла ошибка:\n'
                f'пользователь не в боте, из-за чего он был лишон модерации.')
    for chat_id in ADMINS:
        id = await username_to_id(chat_id)
        if id:
            await bot.send_message(chat_id=id, text=text, parse_mode='html')
        else:
            db[int(id)]["is_subscribed"] = False


@dp.message(Command_chat(commands=['op']), Is_Admin())
async def get_op(msg: types.Message, command: CommandObject):
    await register(msg)
    args = command.args
    if args and msg.chat.type == 'private':
        text = args
        id = await username_to_id(text)
        if id:
            id = int(id)
            if (id not in MODERATORS and
                    id not in ADMINS and
                    f"@{db[id]['info'].username}" not in MODERATORS and
                    f"@{db[id]['info'].username}" not in ADMINS):
                await bot.send_message(chat_id=id, text='Теперь вы модератор!')
                await send_moderators(
                    f'{text} успешно был назначен модератором (from {msg.from_user.id}, @{msg.from_user.username}).')
                MODERATORS.append(text)
            else:
                await msg.reply('Этот пользователь уже админ или модератор.')

        else:
            await msg.reply('Не верное имя пользователя или id.')


@dp.message(Command_chat(commands=['deop']), Is_Admin())
async def del_op(msg: types.Message, command: CommandObject):
    await register(msg)
    args = command.args
    if args and msg.chat.type == 'private':
        text = args
        id = await username_to_id(text)
        if id and text not in ADMINS and text in MODERATORS:
            await bot.send_message(id, 'Вас сняли с модерации.  ):')
            MODERATORS.remove(text)
            await send_moderators(
                f'{text} успешно был снят с модерации ({msg.from_user.id}, @{msg.from_user.username})')
        else:
            await msg.reply('ошибка: нет такого модератора')


@dp.message(Command_chat(commands=['send_all', 'send']), Is_Admin())
async def send(msg: types.Message, command: CommandObject):
    await register(msg)
    text = command.args
    if text and ' ' in text:
        text = text.split(' ', maxsplit=1)
        id = await username_to_id(text[0])
        if id:
            await bot.send_message(chat_id=id, text=text[1])
            await msg.answer(f'send message: \n<b>{text[1]}</b> to user {text[0]}', parse_mode='html')
        else:
            await msg.answer('Неверное имя пользователя или id.')
    elif text:
        text = text
        await msg.answer(f'send message: \n<code>{text}</code>', parse_mode='html')
        for user_id in db.keys():
            if user_id != msg.from_user.id or 1:
                # await sleep(10)
                try:
                    await bot.send_message(user_id, text, parse_mode='html')
                except TelegramForbiddenError:
                    info_user: types.message.User = db[user_id]["info"]
                    await msg.answer(f'''{info_user.full_name} был удален!
Info {user_id}:
    id: <code>{user_id}</code>
    full name: <code>{info_user.full_name}</code>
    first name: <code>{info_user.first_name}</code>
    username: @{info_user.username}
    model: "{db[user_id]['model'] if db[user_id]['model'] != g4f.models.default else "Auto"}"
    language code: "{info_user.language_code}"
''', parse_mode='html')
                    db[int(user_id)]["is_subscribed"] = False


@dp.message(Command_chat(commands=['users', 'get_users']), Is_Admin())
async def get_users(msg: types.Message, command: CommandObject):
    if msg.chat.type != 'private':
        await msg.delete()
    await register(msg)
    id_user = command.args
    if id_user:
        if id_user[0] == '@' or id_user.isnumeric():
            id_user = await username_to_id(id_user)
            if int(id_user) in db.keys():
                info_user = db[int(id_user)]["info"]
                info_user: types.message.User
                await msg.answer(f'''Info {id_user}:

    id: <code>{id_user}</code>
    full name: <code>{info_user.full_name}</code>
    first name: <code>{info_user.first_name}</code>
    username: @{info_user.username}
    model: "{db[int(id_user)]['model'] if db[int(id_user)]['model'] != g4f.models.default else "Auto"}"
    language code: "{info_user.language_code}"
                ''', parse_mode='html')
            else:
                await msg.answer(f'Не удалось найти информацию о пользователе: {msg.text.split(" ")[1]}')
        elif id_user == 'all':
            await msg.answer('Users:\n\n{}'.format(
                ",\n".join([f"<b>{db[id]['info'].full_name}</b> - <code>{id}</code>" for id in db.keys()])),
                parse_mode='html')
        else:
            await msg.answer(f'Ошибка в синтаксисе: {id_user}')
    else:
        await msg.answer(
            f'В боте было зарегистрированно целых <b>{len([True for user in db.values() if user["is_subscribed"]])} людей</b>!',
            parse_mode='html')


@dp.message(Command_chat(commands=['help', 'commands']))
async def help_bot(msg: types.Message):
    admins_and_moderators = ', '.join([', '.join([f'<b>{a}</b>' for a in ADMINS if not a.isnumeric()]),
                                       ', '.join([f'<b>{m}</b>' for m in MODERATORS if not m.isnumeric()])])
    await msg.reply(help_text.format(me.username, admins_and_moderators),
                    parse_mode='html')


@dp.message(Command_chat(commands=['clear']))
async def register(msg: types.Message):
    first_started = msg.from_user.id not in db.keys()

    if msg.from_user.id not in db.keys():
        db[msg.from_user.id] = {'dialog': [], 'is_dialog': False, 'model': g4f.models.default, "is_subscribed": False,
                                "info": msg.from_user}
        print(f'"{msg.from_user.full_name}" успешно зарегестрирован(-а)!')
        for id in ADMINS:
            id = await username_to_id(id)
            if id:
                await bot.send_message(id, f'"{msg.from_user.full_name}" успешно зарегестрирован(-а)!')

    elif msg.text in ['/clear', '/start']:
        db[msg.from_user.id]['is_dialog'] = False
        db[msg.from_user.id]['dialog'] = []
        await msg.reply('Контекст диалога сброшен.')
    db[msg.from_user.id]["is_subscribed"] = True
    # save()
    return first_started


@dp.message(Command(commands=['start', 'restart']))
async def on_start(msg: types.Message, command: CommandObject):
    first_started = await register(msg)
    id = command.args
    if id and str(msg.from_user.id) != id and id.isnumeric():
        id = id.strip()
        if int(id) in db.keys() and first_started:
            await bot.send_message(chat_id=id,
                                   text=f'{msg.from_user.full_name}(@{msg.from_user.username}) открыл твою пригласительную ссылку на нашего бота!')
            await msg.reply(
                f'Привет, {msg.from_user.first_name}, вижу, тебя пригласил(-а) в наш бот {db[int(id)]["info"].full_name}(@{db[int(id)]["info"].username})')

    await msg.reply('Вы успешно вошли/зарегестрированны')
    await msg.answer(f'''Привет! 👋 Я <b>бот</b>, созданный на основе технологии ChatGPT-4, и я здесь, чтобы помочь тебе с различными задачами. Могу поддержать беседу на любую тему, помочь найти информацию, дать совет или просто развлечь интересным фактом. Напиши мне что-нибудь, и давай начнем наше знакомство! 😊

Если ты не знаешь, с чего начать, вот несколько вещей, которые я могу делать:
- <b>📚 Отвечать на общие вопросы</b> и предоставлять объяснения
- <b>🤔 Помогать с решением задач</b> и логических головоломок
- <b>🌐 Предлагать ресурсы</b> для обучения и саморазвития
- <b>📃 Писать и редактировать тексты</b>
- <b>🎲 Предлагать игры</b> и активности для развлечения

Просто напиши свой запрос, и я постараюсь помочь!

И кстати, твоя пригласительная ссылка: <code>t.me/{me.username}?start={msg.from_user.id}</code>
''', parse_mode='html')


@dp.message(Command_chat(commands=['menu']))
async def menu(msg: types.Message):
    buttons = [InlineKeyboardButton(text=model, callback_data=model) for model in supported_models]
    ikb = InlineKeyboardBuilder()
    ikb.row(*buttons, width=2)
    await bot.send_message(chat_id=msg.chat.id, text='Выберите модель.',
                           reply_markup=ikb.as_markup(resize_keyboard=True), reply_to_message_id=msg.message_id)


@dp.callback_query()
async def choice_model(callback: types.CallbackQuery):
    msg = callback.message
    if callback.message.reply_to_message:
        await register(callback.message.reply_to_message)
        if callback.data in supported_models:
            if callback.data.lower() == 'auto':
                db[msg.reply_to_message.from_user.id]['model'] = g4f.models.default
            else:
                db[msg.reply_to_message.from_user.id]['model'] = callback.data

            await callback.answer(f'Выбран {callback.data}', show_alert=True)
            await callback.message.reply_to_message.delete()
            await msg.delete()

        elif callback.data.lower() == 'regenerate':
            messages: list[g4f.typing.Dict] = db[msg.reply_to_message.from_user.id]['dialog']
            await callback.answer()
            try:
                await dialog(msg.reply_to_message, msg,
                             messages[:messages.index({"role": "assistant", "content": msg.text}) - 1])
            except Exception as ex:
                print(ex)
                await msg.delete()
        elif callback.data.lower() == 'close':
            await msg.delete()
            await callback.answer()


@dp.message()
async def dialog(msg: types.Message, msg_replace: types.Message = False, messages: g4f.Messages = False):
    # print(msg.text)
    if msg.content_type == 'new_chat_members' and msg.chat.type != 'private':
        chat_title = msg.chat.title.replace("<", "").replace(">", "")
        await msg.answer(f'Привет, <b>{msg.from_user.first_name}</b>, добро пожаловать в чат <b>{chat_title}</b>',
                         parse_mode='html')
    if msg.content_type == 'text':
        await register(msg)
    if msg.chat.type != 'private' and msg.content_type == 'text' and not msg_replace:
        text = msg.text.split(' ', 1)
        if text[0] == f'@{me.username}':
            message = text[1]
        else:
            return
    else:
        message = msg.text
    if msg.content_type != 'text':
        if msg.chat.type == 'private':
            await msg.reply('Только текст!')
        return
    elif msg.text[0] == '/':
        return
    elif msg.text != '' and not db[msg.from_user.id]['is_dialog']:
        user_dict = db[msg.from_user.id]
        user_dict['is_dialog'] = True
        message = {"role": "user", "content": message}
        user_dict['dialog'].append(message)
        # Get the last n messages
        context = user_dict['dialog'][-10:] if not messages else messages
        user_dict['dialog'] = context
        # Change this number based on the model's context window
        if msg_replace:
            send_msg = await msg_replace.edit_text('⌛️ Ожидайте ответ...', reply_to_message_id=msg.message_id)
        else:
            send_msg = await bot.send_message(msg.chat.id, '⌛️ Ожидайте ответ...', reply_to_message_id=msg.message_id)
        try:
            response = await g4f.ChatCompletion.create_async(
                model=user_dict['model'],
                messages=context,
                stream=False,
                timeout=60 * 5
            )
            message = {"role": "assistant", "content": response}
            # print(response)
            ikb = InlineKeyboardBuilder([[InlineKeyboardButton(text='Regenerate', callback_data='regenerate')]])
            if message['content'] and send_msg.text != context:
                context.append(message)
                try:
                    await send_msg.edit_text(reply_to_message_id=msg.message_id,
                                             text=message["content"], reply_markup=ikb.as_markup())
                except TelegramForbiddenError:
                    db[msg.from_user.id]['is_subscribed'] = False
        except Exception as ex:
            ikb = InlineKeyboardBuilder([[InlineKeyboardButton(text='Close', callback_data='close')]])
            try:
                await send_msg.edit_text(
                    'При генерации произошла ошибка! повторите попытку или используйте другую модель!',
                    reply_markup=ikb.as_markup(), reply_to_message_id=msg.message_id)
                if not msg_replace:
                    await msg.answer(str(ex))
            except Exception as ex:
                print(ex)
            print(ex)
        user_dict['dialog'] = context
        ok = await msg.answer('Генерация окончена')
        await sleep(2)
        await ok.delete()
        user_dict['is_dialog'] = False
    elif db[msg.from_user.id]['is_dialog']:
        await msg.reply('Нельзя писать во время генерации текста, бот думает!')


# def has_special_char(s):
#     return any(char in string.punctuation for char in s)


async def main():
    global me
    me = await bot.get_me()
    await dp.start_polling(bot)


if __name__ == '__main__':
    run(main())
