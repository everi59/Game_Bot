from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
import locale
from bot import bot
from data.sql_database import LobbyDatabase, UsersWithoutLobbiesDatabase
from keyboards.keyboards import create_inline_kb, LobbyCallbackFactory
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.storage.base import StorageKey
from services.services import FSMLobbyClass, create_lobbies_page, send_messages_to_users, get_lobby_members

router = Router()
lobby_database = LobbyDatabase('test6')
users_without_lobbies_database = UsersWithoutLobbiesDatabase('test5')
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')


@router.message(Command(commands='start'))
async def start(message: Message,
                state: FSMContext):
    data = await state.get_data()
    if data.get('lobby'):
        await state.update_data(lobby=None)
        await lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id),
                                        user_name=message.from_user.full_name)
        lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
        if not len(lobby_stat):
            await lobby_database.delete_lobby(data['lobby'])
        else:
            await send_messages_to_users(bot=bot,
                                         message=f'{message.from_user.full_name} вышел(-а) из лобби\n\n'
                                                 f'Текущие участники:\n'
                                                 f'{get_lobby_members(lobby_stat)}\n\n'
                                                 f'Приготовиться - /ready\n'
                                                 f'Информация о лобби - /info\n'
                                                 f'Выйти - /exit',
                                         users=lobby_stat)
        lobby_pages = create_lobbies_page()
        keyboard = create_inline_kb(width=2, dct=lobby_pages)
        people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
        for chat_id, message_id in people_without_lobby:
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                    reply_markup=keyboard)
            except TelegramBadRequest:
                pass
    await state.set_state(default_state)
    await message.answer(text='Это тренировочный бот для игры в ... с другими людьми.\nДля начала выберите лобби,'
                              ' использовав команду /lobbies')


@router.message(Command(commands='lobbies'), ~StateFilter(FSMLobbyClass.select_lobby))
async def lobbies(message: Message,
                  state: FSMContext):
    await state.set_state(FSMLobbyClass.select_lobby)
    data = await state.get_data()
    people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
    if data.get('lobby'):
        await state.update_data(lobby=None)
        await lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id),
                                        user_name=message.from_user.full_name)
        lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
        if not len(lobby_stat):
            await lobby_database.delete_lobby(data['lobby'])
        else:
            await send_messages_to_users(bot=bot,
                                         message=f'{message.from_user.full_name} вышел(-a) из лобби\n\n'
                                                 f'Текущие участники:\n'
                                                 f'{get_lobby_members(lobby_stat)}\n\n'
                                                 f'Приготовиться - /ready\n'
                                                 f'Информация о лобби - /info\n'
                                                 f'Выйти - /exit',
                                         users=lobby_stat)
        lobby_pages = create_lobbies_page()
        keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby')
        for chat_id, message_id in people_without_lobby:
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                    reply_markup=keyboard)
            except TelegramBadRequest:
                pass
    lobby_pages = create_lobbies_page()
    keyboards = create_inline_kb(2, dct=lobby_pages, last_btn='create_new_lobby')
    bot_message = await message.answer(text='Список доступных лобби', reply_markup=keyboards)
    await users_without_lobbies_database.insert_users_message_id(chat_id=message.chat.id,
                                                                 message_id=bot_message.message_id)


@router.callback_query(LobbyCallbackFactory.filter(), StateFilter(FSMLobbyClass.select_lobby))
async def lobby_page(callback: CallbackQuery,
                     callback_data: LobbyCallbackFactory,
                     state: FSMContext):
    lobby_stat_1 = lobby_database.get_lobby_stat(callback_data.lobby_id)
    if len(lobby_stat_1) < 4:
        await state.update_data(lobby=callback_data.lobby_id, ready=0)
        await state.set_state(FSMLobbyClass.in_lobby)
        await lobby_database.enter_lobby(lobby_id=callback_data.lobby_id, user_chat_id=str(callback.message.chat.id),
                                         user_name=callback.from_user.full_name)
        lobby_pages = create_lobbies_page()
        keyboard = create_inline_kb(width=2, dct=lobby_pages)
        lobby_stat = lobby_database.get_lobby_stat(callback_data.lobby_id)
        await callback.message.edit_text(text=f'Вы вошли(-а) в лобби!\n\n'
                                              f'Участники:\n'
                                              f'{get_lobby_members(lobby_stat)}\n\n'
                                              f'Приготовиться - /ready\n'
                                              f'Информация о лобби - /info\n'
                                              f'Выйти - /exit',
                                         reply_markup=None)
        await users_without_lobbies_database.delete_chat_id(chat_id=callback.message.chat.id)
        people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
        for chat_id, message_id in people_without_lobby:
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                    reply_markup=keyboard)
            except TelegramBadRequest:
                pass

        await send_messages_to_users(bot=bot,
                                     message=f'{callback.from_user.full_name} зашел(-а) в лобби\n\n'
                                             f'Текущие участники:\n'
                                             f'{get_lobby_members(lobby_stat)}\n\n'
                                             f'Приготовиться - /ready\n'
                                             f'Информация о лобби - /info\n'
                                             f'Выйти - /exit',
                                     users=lobby_stat_1)
    else:
        await callback.answer('Лобби заполнено')


@router.message(Command(commands='exit'), StateFilter(FSMLobbyClass.in_lobby))
async def exit_command(message: Message,
                       state: FSMContext):
    data = await state.get_data()
    await lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id),
                                    user_name=message.from_user.full_name)
    lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
    if not len(lobby_stat[0]):
        await lobby_database.delete_lobby(data['lobby'])
    else:
        await send_messages_to_users(bot=bot,
                                     message=f'{message.from_user.full_name} вышел(-а) из лобби\n\n'
                                             f'Текущие участники:\n'
                                             f'{get_lobby_members(lobby_stat)}\n\n'
                                             f'Приготовиться - /ready\n'
                                             f'Информация о лобби - /info\n'
                                             f'Выйти - /exit',
                                     users=lobby_stat)
    lobby_pages = create_lobbies_page()
    keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby')
    bot_message = await message.answer(text='Список доступных лобби', reply_markup=keyboard)
    people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
    await state.update_data(lobby=None)
    await state.set_state(FSMLobbyClass.select_lobby)
    await users_without_lobbies_database.insert_users_message_id(chat_id=message.chat.id,
                                                                 message_id=bot_message.message_id)
    for chat_id, message_id in people_without_lobby:
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                reply_markup=keyboard)
        except TelegramBadRequest:
            pass


@router.message(Command(commands='info'), StateFilter(FSMLobbyClass.in_lobby))
async def info_command(message: Message,
                       state: FSMContext):
    data = await state.get_data()
    lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
    await message.answer(text=f'Участники:\n'
                              f'{get_lobby_members(lobby_stat)}\n\n'
                              f'Приготовиться - /ready\n'
                              f'Выйти - /exit')


@router.message(Command(commands='ready'), StateFilter(FSMLobbyClass.in_lobby))
async def ready_command_others(message: Message,
                               state: FSMContext):
    storage = state.storage
    data = await state.get_data()
    storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
                                                     chat_id=message.chat.id,
                                                     user_id=message.chat.id))
    print(storage_data)
    if not storage_data['ready']:
        storage_data['ready'] = 1
        await storage.update_data(StorageKey(bot_id=bot.id,
                                             chat_id=message.chat.id,
                                             user_id=message.chat.id), data=storage_data)
        users_unready = []
        users_unready_counter = 0
        lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
        answer_for_other_text = f'{message.from_user.full_name} готов к игре!\n\n'
        other_text = ''
        for pair in lobby_stat:
            print(pair)
            storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
                                                             chat_id=int(pair.split('-')[0]),
                                                             user_id=int(pair.split('-')[0])))
            print(storage_data)
            if storage_data['ready']:
                users_unready.append(f'{pair.split("-")[1]} - готов')
            else:
                users_unready_counter += 1
                users_unready.append(f'{pair.split("-")[1]} - не готов')
        if users_unready_counter == 0:
            if len(lobby_stat) == 2:
                other_text += ('Все игроки готовы! Игра начинается!\n\n'
                               'Информация о лобби - /info\n'
                               'Выйти - /exit')
                for pair in lobby_stat:
                    await storage.set_state(StorageKey(bot_id=bot.id,
                                                       chat_id=int(pair.split('-')[0]),
                                                       user_id=int(pair.split('-')[0])), state=FSMLobbyClass.in_game)

            else:
                other_text += '\n'.join(users_unready)
                other_text += ('\n\nОжидаем других игроков\n\n'
                               'Информация о лобби - /info\n'
                               'Выйти - /exit')
        else:
            other_text += '\n'.join(users_unready)
            other_text += ('\n\nОжидаем других игроков\n\n'
                           'Информация о лобби - /info\n'
                           'Выйти - /exit')
        await message.answer(text='Вы приготовились!\n\n'+other_text)
        for pair in lobby_stat:
            if pair.split('-')[0] != str(message.chat.id):
                await bot.send_message(chat_id=pair.split('-')[0], text=answer_for_other_text+other_text)
    else:
        await message.answer(text='Вы уже готовы!')


@router.callback_query(F.data == 'create_new_lobby', StateFilter(FSMLobbyClass.select_lobby))
async def create_new_lobby(callback: CallbackQuery,
                           state: FSMContext):
    lobby_id = lobby_database.create_new_lobby(user_chat_id=str(callback.message.chat.id),
                                               user_name=callback.from_user.full_name)
    await state.set_state(FSMLobbyClass.in_lobby)
    await state.update_data(lobby=lobby_id, ready=0)
    await callback.message.edit_text(text='Вы создали новое лобби!\n\n'
                                          'Приготовиться - /ready\n'
                                          'Информация о лобби - /info\n'
                                          'Выйти - /exit')
    await users_without_lobbies_database.delete_chat_id(chat_id=callback.message.chat.id)
    people_without_lobby = users_without_lobbies_database.get_statistic_of_users()
    if people_without_lobby:
        lobby_pages = create_lobbies_page()
        keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby')
        for chat_id, message_id in people_without_lobby:
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                    reply_markup=keyboard)
            except TelegramBadRequest:
                pass
    print(lobby_database.get_lobby_stat(lobby_id=lobby_id))


@router.message(StateFilter(FSMLobbyClass.in_game))
async def game(message: Message,
               state: FSMContext):
    await message.answer(text='Вы играити, ура')
