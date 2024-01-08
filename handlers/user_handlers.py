from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery
from bot import bot, users_database, lobby_database
from keyboards.keyboards import create_inline_kb, LobbyCallbackFactory
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from services.services import exit_lobby, FSMLobbyClass, create_lobbies_page, create_deck, LobbyMessage, \
    update_previous_pages
from datetime import datetime
from lexicon.lexicon import lexicon_menu_keyboard, lexicon_user_statistic
from copy import deepcopy

router = Router()


@router.message(Command(commands='start'))
async def start(message: Message,
                state: FSMContext):
    data = await state.get_data()
    await users_database.insert_new_user(chat_id=message.chat.id, user_name=message.chat.full_name)
    await users_database.delete_lobbies_page_message_id(chat_id=message.chat.id)
    if data.get('lobby'):
        await exit_lobby(state=state, data=data, bot=bot, message=message)
    await state.set_state(default_state)
    keyboard = create_inline_kb(dct={'menu': 'Главное меню'}, width=1)
    game_message_id = await message.answer(text='Это тренировочный бот для игры в <b>Дурака</b> с другими людьми.\n'
                                                'Для начала перейдите в главное меню',
                                           reply_markup=keyboard)
    await state.update_data(previous_pages=[], game_message_id=game_message_id.message_id)


@router.callback_query(F.data == 'menu', StateFilter(default_state, FSMLobbyClass.select_lobby))
async def menu(callback: CallbackQuery,
               state: FSMContext):
    data = await state.get_data()
    data_callback = callback.data
    data = update_previous_pages(data, data_callback)
    await state.update_data(data=data)
    await state.set_state(default_state)
    keyboard = create_inline_kb(dct=lexicon_menu_keyboard, width=1)
    await callback.message.edit_text(text='Вы находитесь в главном меню', reply_markup=keyboard)
    data['previous_pages'].append(callback.data)


@router.callback_query(F.data == 'statistics', StateFilter(default_state))
async def statistic(callback: CallbackQuery,
                    state: FSMContext):
    data = await state.get_data()
    data_callback = callback.data
    data = update_previous_pages(data, data_callback)
    await state.update_data(data=data)
    user_stat = users_database.get_user_statistic(chat_id=callback.message.chat.id)
    keyboard = create_inline_kb(width=1, back_button=data['previous_pages'][-1])
    await callback.message.edit_text(text=lexicon_user_statistic.format(*user_stat), reply_markup=keyboard)
    data['previous_pages'].append(callback.data)


@router.callback_query(F.data == 'free_reward', StateFilter(default_state))
async def free_reward(callback: CallbackQuery):
    balance = users_database.get_user_balance(chat_id=callback.message.chat.id)
    if balance < 1450:
        last_date = users_database.get_last_free_reward_date_timestamp(chat_id=callback.message.chat.id)
        current_date = datetime.now().timestamp()
        difference_date = current_date - last_date
        if difference_date >= 3600:
            await callback.answer(text='Беcплатная награда выдана (+1450)')
            balance += 1450
            users_database.update_user_balance(chat_id=callback.message.chat.id, balance=balance)
            users_database.update_last_free_reward_date_timestamp(chat_id=callback.message.chat.id,
                                                                  last_free_reward_date_timestamp=current_date)
        else:
            normal_date = datetime.fromtimestamp(last_date+3600)
            await callback.answer(text=f'Следующую награду можно получить в {normal_date.strftime("%X")}',
                                  show_alert=True)
    else:
        await callback.answer(text='У вас достаточно средств', show_alert=True)


@router.callback_query(F.data == 'lobbies', StateFilter(default_state))
async def lobbies(callback: CallbackQuery,
                  state: FSMContext):
    data = await state.get_data()
    data_callback = callback.data
    data = update_previous_pages(data, data_callback)
    await state.update_data(data=data)
    await state.set_state(FSMLobbyClass.select_lobby)
    if data.get('lobby'):
        await exit_lobby(state=state, data=data, bot=bot, message=callback.message)
    lobby_pages = create_lobbies_page()
    keyboards = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby',
                                 back_button=data['previous_pages'][-1])
    bot_message = await callback.message.edit_text(text='Список доступных лобби', reply_markup=keyboards)
    await users_database.update_lobbies_page_message_id(chat_id=callback.message.chat.id,
                                                        lobbies_page_message_id=bot_message.message_id)
    data['previous_pages'].append(callback.data)


@router.callback_query(LobbyCallbackFactory.filter(), StateFilter(FSMLobbyClass.select_lobby))
async def lobby_page(callback: CallbackQuery,
                     callback_data: LobbyCallbackFactory,
                     state: FSMContext):
    lobby_stat = lobby_database.get_lobby_stat(callback_data.lobby_id)
    if len(lobby_stat) < 4:
        users_name = users_database.get_user_name(chat_id=callback.message.chat.id)
        lobby_user_ids = deepcopy(lobby_stat)
        lobby_user_ids.append(callback.message.chat.id)
        lobby_message = LobbyMessage([users_database.get_user_name(chat_id) for chat_id in lobby_user_ids])
        keyboard = create_inline_kb(dct=lobby_message.lobby_keyboard_buttons, width=1)
        bot_message = await callback.message.edit_text(text=str(lobby_message), reply_markup=keyboard)
        await callback.answer(text='Вы зашли в лобби!')
        await users_database.delete_lobbies_page_message_id(chat_id=callback.message.chat.id)
        users_database.update_game_page_message_id(chat_id=callback.message.chat.id, message_id=bot_message.message_id)
        people_without_lobby = users_database.get_statistic_of_users_without_lobby()
        storage = state.storage
        for chat_id in lobby_stat:
            try:
                storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
                                                                 chat_id=int(chat_id),
                                                                 user_id=int(chat_id)))
                lobby_message = storage_data['lobby_message']
                lobby_message.add_user(users_name)
                await bot.edit_message_text(text=str(lobby_message), chat_id=chat_id,
                                            message_id=users_database.get_user_game_page_message_id(
                                                chat_id=chat_id),
                                            reply_markup=lobby_message.keyboard)
            except TelegramBadRequest:
                pass
        for chat_id, message_id in people_without_lobby:
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                    reply_markup=keyboard)
            except TelegramBadRequest:
                pass
        await lobby_database.enter_lobby(lobby_id=callback_data.lobby_id, user_chat_id=str(callback.message.chat.id))
        await state.set_state(FSMLobbyClass.in_lobby)
    else:
        await callback.answer('Лобби заполнено')
#
#
# @router.message(Command(commands='exit'), StateFilter(FSMLobbyClass.in_lobby))
# async def exit_command(message: Message,
#                        state: FSMContext):
#     data = await state.get_data()
#     await lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id),
#                                     user_name=message.from_user.full_name)
#     lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
#     if not len(lobby_stat[0]):
#         await lobby_database.delete_lobby(data['lobby'])
#     else:
#         await send_messages_to_users(bot=bot,
#                                      message=f'{message.from_user.full_name} вышел(-а) из лобби\n\n'
#                                              f'Текущие участники:\n'
#                                              f'{get_lobby_members(lobby_stat)}\n\n'
#                                              f'Приготовиться - /ready\n'
#                                              f'Информация о лобби - /info\n'
#                                              f'Выйти - /exit',
#                                      users=lobby_stat)
#     lobby_pages = create_lobbies_page()
#     keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby')
#     bot_message = await message.answer(text='Список доступных лобби', reply_markup=keyboard)
#     people_without_lobby = users_database.get_statistic_of_users_without_lobby()
#     await state.update_data(lobby=None)
#     await state.set_state(FSMLobbyClass.select_lobby)
#     await users_database.insert_users_message_id(chat_id=message.chat.id,
#                                                                  message_id=bot_message.message_id)
#     for chat_id, message_id in people_without_lobby:
#         try:
#             await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
#                                                 reply_markup=keyboard)
#         except TelegramBadRequest:
#             pass
#     if data.get('current_cards'):
#         lobby_deck = lobby_database.get_lobby_deck(lobby_id=data['lobby']).split('~~~')
#         user_cards = data['current_cards'].split('~~~')
#         for card in user_cards:
#             lobby_deck.append(card)
#         await lobby_database.update_deck(deck='~~~'.join(lobby_deck))
#
#
# @router.message(Command(commands='info'), StateFilter(FSMLobbyClass.in_lobby))
# async def info_command(message: Message,
#                        state: FSMContext):
#     data = await state.get_data()
#     lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
#     await message.answer(text=f'Участники:\n'
#                               f'{get_lobby_members(lobby_stat)}\n\n'
#                               f'Приготовиться - /ready\n'
#                               f'Выйти - /exit')
#
#
# @router.message(Command(commands='ready'), StateFilter(FSMLobbyClass.in_lobby))
# async def ready_command_others(message: Message,
#                                state: FSMContext):
#     storage = state.storage
#     data = await state.get_data()
#     storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
#                                                      chat_id=message.chat.id,
#                                                      user_id=message.chat.id))
#     if not storage_data['ready']:
#         deck = lobby_database.get_lobby_deck(lobby_id=data['lobby'])
#         cards = get_next_cards(deck=deck, cards_num=6)
#         storage_data['ready'] = 1
#         storage_data['current_cards'] = cards[0]
#         deck = '~~~'.join(cards[1])
#         await lobby_database.update_deck(deck=deck, lobby_id=data['lobby'])
#         await storage.update_data(StorageKey(bot_id=bot.id,
#                                              chat_id=message.chat.id,
#                                              user_id=message.chat.id), data=storage_data)
#         users_unready = []
#         users_unready_counter = 0
#         lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
#         answer_for_other_text = f'{message.from_user.full_name} готов к игре!\n\n'
#         other_text = ''
#         user_cards = {}
#         info_text = '\n\nИнформация о лобби - /info\nВыйти - /exit'
#         print(storage_data)
#         for pair in lobby_stat:
#             print(pair)
#             storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
#                                                              chat_id=int(pair.split('-')[0]),
#                                                              user_id=int(pair.split('-')[0])))
#             if storage_data['ready']:
#                 users_unready.append(f'{pair.split("-")[1]} - готов')
#             else:
#                 users_unready_counter += 1
#                 users_unready.append(f'{pair.split("-")[1]} - не готов')
#         if users_unready_counter == 0:
#             if len(lobby_stat) == 2:
#                 other_text = 'Все игроки готовы! Игра начинается!\n\nВаши карты:\n'
#                 for pair in lobby_stat:
#                     await storage.set_state(StorageKey(bot_id=bot.id,
#                                                        chat_id=int(pair.split('-')[0]),
#                                                        user_id=int(pair.split('-')[0])), state=FSMLobbyClass.in_game)
#                     storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
#                                                                      chat_id=int(pair.split('-')[0]),
#                                                                      user_id=int(pair.split('-')[0])))
#                     user_cards[int(pair.split('-')[0])] = sorted([x.replace('-', ' ')
#                                                                   for x in storage_data['current_cards']],
#                                                                  key=lambda x: (lexicon_card_colors[x.split()[1]],
#                                                                                 lexicon_card_faces[x.split()[0]]))
#
#             else:
#                 other_text += '\n'.join(users_unready)
#                 other_text += '\n\nОжидаем других игроков'
#         else:
#             other_text += '\n'.join(users_unready)
#             other_text += '\n\nОжидаем других игроков'
#         for pair in lobby_stat:
#             if pair.split('-')[0] != str(message.chat.id):
#                 if user_cards:
#                     await bot.send_message(chat_id=pair.split('-')[0],
#                                            text=answer_for_other_text + other_text + '\n'.join(user_cards[
#                                                int(pair.split('-')[0])]) + info_text)
#                 else:
#                     await bot.send_message(chat_id=pair.split('-')[0],
#                                            text=answer_for_other_text + other_text + info_text)
#             else:
#                 if user_cards:
#                     await message.answer(text='Вы приготовились!\n\n'+other_text+'\n'.join(user_cards[
#                         int(pair.split('-')[0])])+info_text)
#                 else:
#                     await message.answer(text='Вы приготовились!\n\n'+other_text+info_text)
#     else:
#         await message.answer(text='Вы уже готовы!')


@router.callback_query(F.data == 'create_new_lobby', StateFilter(FSMLobbyClass.select_lobby))
async def create_new_lobby(callback: CallbackQuery,
                           state: FSMContext):
    deck = create_deck()
    lobby_id = lobby_database.create_new_lobby(user_chat_id=str(callback.message.chat.id), deck=deck)
    lobby_message = LobbyMessage([callback.message.chat.full_name])
    bot_message = await callback.message.edit_text(text=str(lobby_message), reply_markup=lobby_message.keyboard)
    await callback.answer(text='Вы создали лобби!')
    await state.set_state(FSMLobbyClass.in_lobby)
    await state.update_data(lobby=lobby_id, ready=0, lobby_message=lobby_message)
    await users_database.delete_lobbies_page_message_id(chat_id=callback.message.chat.id)
    users_database.update_game_page_message_id(chat_id=callback.message.chat.id, message_id=bot_message.message_id)
    people_without_lobby = users_database.get_statistic_of_users_without_lobby()
    lobby_pages = create_lobbies_page()
    keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby')
    for chat_id, message_id in people_without_lobby:
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                reply_markup=keyboard)
        except TelegramBadRequest:
            pass
