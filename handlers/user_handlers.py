from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery

from bot import bot
from data.sql_database import LobbyDatabase, UsersWithoutLobbiesDatabase
from keyboards.keyboards import create_inline_kb, LobbyCallbackFactory
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from services.services import FSMLobbyClass, create_lobbies_page, send_messages_to_users, get_lobby_members

router = Router()
lobby_database = LobbyDatabase('test6')
users_without_lobbies_database = UsersWithoutLobbiesDatabase('test5')


@router.message(Command(commands='start'))
async def start(message: Message,
                state: FSMContext):
    await message.answer(text='Это тренировочный бот для игры в ... с другими людьми.\nДля начала выберите лобби,'
                              ' использовав команду /lobbies')
    users_without_lobbies_database.insert_users_message_id(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(default_state)


@router.message(Command(commands='lobbies'), StateFilter(default_state))
async def lobbies(message: Message,
                  state: FSMContext):
    lobby_pages = create_lobbies_page()
    keyboards = create_inline_kb(2, dct=lobby_pages)
    bot_message = await message.answer(text='Список доступных лобби', reply_markup=keyboards)
    await state.set_state(FSMLobbyClass.select_lobby)
    users_without_lobbies_database.update_users_message_id(chat_id=message.chat.id, message_id=bot_message.message_id)


@router.callback_query(LobbyCallbackFactory.filter(), StateFilter(FSMLobbyClass.select_lobby))
async def lobby_page(callback: CallbackQuery,
                     callback_data: LobbyCallbackFactory,
                     state: FSMContext):
    lobby_stat = lobby_database.get_lobby_stat(callback_data.lobby_id)
    if len(lobby_stat) < 4:
        await state.set_state(FSMLobbyClass.in_lobby)
        lobby_database.enter_lobby(lobby_id=callback_data.lobby_id, user_chat_id=str(callback.message.chat.id),
                                   user_name=callback.from_user.full_name)
        users_without_lobbies_database.delete_chat_id(chat_id=callback.message.chat.id)
        people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
        lobby_pages = create_lobbies_page()
        keyboard = create_inline_kb(width=2, dct=lobby_pages)
        for chat_id, message_id in people_without_lobby:
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                    reply_markup=keyboard)
            except TelegramBadRequest:
                pass
        await state.update_data(lobby=callback_data.lobby_id)
        await send_messages_to_users(bot=bot, message=f'{callback.from_user.full_name} зашел в лобби', users=lobby_stat)
        await callback.message.delete()
        lobby_stat = lobby_database.get_lobby_stat(callback_data.lobby_id)
        await callback.message.answer(text=f'Вы вошли в лобби №{callback_data.lobby_id}!\n\n'
                                           f'Участники:\n'
                                           f'{get_lobby_members(lobby_stat)}\n\n'
                                           f'Информация о лобби - /info\n'
                                           f'Выйти - /exit')
    else:
        await callback.answer('Лобби заполнено')


@router.message(Command(commands='exit'), StateFilter(FSMLobbyClass.in_lobby))
async def exit_command(message: Message,
                       state: FSMContext):
    data = await state.get_data()
    await state.clear()
    lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id),
                              user_name=message.from_user.full_name)
    lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
    await send_messages_to_users(bot=bot, message=f'{message.from_user.full_name} Вышел из лобби', users=lobby_stat)
    lobby_pages = create_lobbies_page()
    people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
    keyboard = create_inline_kb(width=2, dct=lobby_pages)
    for chat_id, message_id in people_without_lobby:
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    await state.set_state(FSMLobbyClass.select_lobby)
    bot_message = await message.answer(text='Список доступных лобби', reply_markup=keyboard)
    users_without_lobbies_database.insert_users_message_id(chat_id=message.chat.id, message_id=bot_message.message_id)


@router.message(Command(commands='info'), StateFilter(FSMLobbyClass.in_lobby))
async def info_command(message: Message,
                       state: FSMContext):
    data = await state.get_data()
    lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
    await message.answer(text=f'Лобби №{data["lobby"]}\n\n'
                              f'Участники:\n'
                              f'{get_lobby_members(lobby_stat)}\n\n'
                              f'Выйти - /exit')


@router.message(StateFilter(FSMLobbyClass.in_lobby))
async def others(message: Message,
                 state: FSMContext):
    data = await state.get_data()
    people = lobby_database.get_lobby_stat(data['lobby'])
    for i in people:
        if int(i.split('-')[0]) != message.chat.id:
            await bot.send_message(chat_id=int(i), text=f"""{message.from_user.full_name}: {message.text}""")


@router.message(Command(commands='test'))
async def test(message: Message):
    people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
    lobby_pages = create_lobbies_page()
    keyboard = create_inline_kb(2, dct=lobby_pages)
    for chat_id, message_id in people_without_lobby:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                            reply_markup=keyboard)
