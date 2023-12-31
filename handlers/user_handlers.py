from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery

from bot import bot
from data.sql_database import LobbyDatabase
from keyboards.keyboards import keyboard_builder, create_inline_kb, LobbyCallbackFactory
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from services.services import FSMLobbyClass, create_lobbies_page

router = Router()
lobby_database = LobbyDatabase('test3')


# @router.message(Command(commands='start'))
# async def start(message: Message):


@router.message(Command(commands='lobbies'), StateFilter(default_state))
async def test2(message: Message,
                state: FSMContext):
    lobby_pages = create_lobbies_page()
    keyboards = create_inline_kb(2, dct=lobby_pages)
    await message.answer(text='Список доступных лобби', reply_markup=keyboards)
    await state.set_state(FSMLobbyClass.select_lobby)
    lobby_database.enter_lobby(lobby_id=-1, user_chat_id=str(message.chat.id))


@router.callback_query(LobbyCallbackFactory.filter(), StateFilter(FSMLobbyClass.select_lobby))
async def lobby_page(callback: CallbackQuery,
                     callback_data: LobbyCallbackFactory,
                     state: FSMContext):
    lobby_stat = lobby_database.get_lobby_stat(callback_data.lobby_id)
    if len(lobby_stat) < 4:
        await state.set_state(FSMLobbyClass.in_lobby)
        lobby_database.enter_lobby(lobby_id=callback_data.lobby_id, user_chat_id=str(callback.message.chat.id))
        lobby_database.exit_lobby(lobby_id=-1, user_chat_id=str(callback.message.chat.id))
        people_without_lobby = lobby_database.get_lobby_stat(-1)
        lobby_pages = create_lobbies_page()
        for i in people_without_lobby:
            await bot.edit_message_text(chat_id=int(i), text='Список доступных лобби', reply_markup=lobby_pages)
        await state.update_data(lobby=callback_data.lobby_id)
        for i in lobby_stat:
            await bot.send_message(chat_id=int(i), text=f'{callback.from_user.full_name} зашел в лобби')
        await callback.message.delete()
        await callback.message.answer(text=f'Вы вошли в лобби №{callback_data.lobby_id}! Любое ваше сообщение будет '
                                           f'отправлено участникам лобби!',
                                      reply_markup=keyboard_builder(buttons=['Выйти'],
                                                                    width=1))
    else:
        await callback.answer('Лобби заполнено')


@router.message(F.text == 'Выйти', StateFilter(FSMLobbyClass.in_lobby))
async def exit_command(message: Message,
                       state: FSMContext):
    await state.set_state(FSMLobbyClass.select_lobby)
    data = await state.get_data()
    lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id))
    lobby_database.enter_lobby(lobby_id=-1, user_chat_id=str(message.chat.id))
    lobby_pages = create_lobbies_page()
    keyboards = create_inline_kb(2, dct=lobby_pages)
    await message.answer(text='Список доступных лобби', reply_markup=keyboards)


@router.message(StateFilter(FSMLobbyClass.in_lobby))
async def others(message: Message,
                 state: FSMContext):
    data = await state.get_data()
    people = lobby_database.get_lobby_stat(data['lobby'])
    for i in people:
        if int(i) != message.chat.id:
            await bot.send_message(chat_id=int(i), text=message.text)