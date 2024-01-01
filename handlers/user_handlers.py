from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery

from bot import bot
from data.sql_database import LobbyDatabase, UsersWithoutLobbiesDatabase
from keyboards.keyboards import keyboard_builder, create_inline_kb, LobbyCallbackFactory
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from services.services import FSMLobbyClass, create_lobbies_page, send_messages_to_users

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
        lobby_database.enter_lobby(lobby_id=callback_data.lobby_id, user_chat_id=str(callback.message.chat.id))
        users_without_lobbies_database.delete_chat_id(chat_id=callback.message.chat.id)
        people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
        lobby_pages = create_lobbies_page()
        keyboard = create_inline_kb(width=2, dct=lobby_pages)
        for chat_id, message_id in people_without_lobby:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                reply_markup=keyboard)
        await state.update_data(lobby=callback_data.lobby_id)
        await send_messages_to_users(bot=bot, message=f'{callback.from_user.full_name} зашел в лобби', users=lobby_stat)
        await callback.message.delete()
        await callback.message.answer(text=f'Вы вошли в лобби №{callback_data.lobby_id}! Любое ваше сообщение будет '
                                           f'отправлено участникам лобби!\n'
                                           f'Для выхода нажмите /exit')
    else:
        await callback.answer('Лобби заполнено')


@router.message(Command(commands='exit'), StateFilter(FSMLobbyClass.in_lobby))
async def exit_command(message: Message,
                       state: FSMContext):
    await state.set_state(FSMLobbyClass.select_lobby)
    data = await state.get_data()
    lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id))
    lobby_pages = create_lobbies_page()
    keyboards = create_inline_kb(width=2, dct=lobby_pages)
    bot_message = await message.answer(text='Список доступных лобби', reply_markup=keyboards)
    users_without_lobbies_database.insert_users_message_id(chat_id=message.chat.id, message_id=bot_message.message_id)


@router.message(StateFilter(FSMLobbyClass.in_lobby))
async def others(message: Message,
                 state: FSMContext):
    data = await state.get_data()
    people = lobby_database.get_lobby_stat(data['lobby'])
    for i in people:
        if int(i) != message.chat.id:
            await bot.send_message(chat_id=int(i), text=message.text)


# @router.message(Command(commands='test'))
# async def test(message: Message):
#     people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
#     lobby_pages = create_lobbies_page()
#     keyboard = create_inline_kb(2, dct=lobby_pages)
#     for chat_id, message_id in people_without_lobby:
#         await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
#                                             reply_markup=keyboard)
