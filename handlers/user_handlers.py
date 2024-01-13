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
    update_previous_pages, GameMessage, lobbies_messages_dict, games_messages_dict
from datetime import datetime
from lexicon.lexicon import lexicon_menu_keyboard, lexicon_user_statistic

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
    await message.answer(text='Это тренировочный бот для игры в <b>Дурака</b> с другими людьми.\n'
                              'Для начала перейдите в главное меню',
                         reply_markup=keyboard)
    await state.update_data(previous_pages=[],
                            user_name=users_database.get_user_name(chat_id=message.chat.id))


@router.callback_query(F.data == 'menu', StateFilter(default_state, FSMLobbyClass.select_lobby))
async def menu(callback: CallbackQuery,
               state: FSMContext):
    data = await state.get_data()
    await state.set_state(default_state)
    keyboard = create_inline_kb(dct=lexicon_menu_keyboard, width=1)
    await callback.message.edit_text(text='Вы находитесь в главном меню', reply_markup=keyboard)
    data['previous_pages'].append(callback.data)
    await state.update_data(data=data)


@router.callback_query(F.data == 'statistics', StateFilter(default_state))
async def statistic(callback: CallbackQuery,
                    state: FSMContext):
    data = await state.get_data()
    data_callback = callback.data
    data = update_previous_pages(data, data_callback)
    user_stat = users_database.get_user_statistic(chat_id=callback.message.chat.id)
    keyboard = create_inline_kb(width=1, back_button=data['previous_pages'][-1])
    await callback.message.edit_text(text=lexicon_user_statistic.format(*user_stat), reply_markup=keyboard)
    data['previous_pages'].append(callback.data)
    await state.update_data(previous_pages=data['previous_pages'])


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
    await state.update_data(previous_pages=data['previous_pages'])


@router.callback_query(LobbyCallbackFactory.filter(), StateFilter(FSMLobbyClass.select_lobby))
async def lobby_page(callback: CallbackQuery,
                     callback_data: LobbyCallbackFactory,
                     state: FSMContext):
    lobby_stat = lobby_database.get_lobby_stat(callback_data.lobby_id)
    if len(lobby_stat) < 4:
        data = await state.get_data()
        user_name = data['user_name']
        await users_database.delete_lobbies_page_message_id(chat_id=callback.message.chat.id)
        people_without_lobby = users_database.get_statistic_of_users_without_lobby()
        lobby_pages = create_lobbies_page()
        lobby_message = lobbies_messages_dict.get(callback_data.lobby_id)
        lobby_message.update_ready_info(ready=0, user=user_name)
        if lobby_message:
            lobby_message.add_user(user_name)
            for chat_id in lobby_stat:
                try:
                    user_name = lobby_message.return_message(users_database.get_user_name(chat_id))
                    await bot.edit_message_text(text=user_name,
                                                chat_id=chat_id,
                                                message_id=users_database.get_user_game_page_message_id(
                                                    chat_id=chat_id),
                                                reply_markup=lobby_message.create_keyboard(user_name))
                except TelegramBadRequest:
                    pass
            for chat_id, message_id in people_without_lobby:
                try:
                    keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby',
                                                back_button='menu')
                    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                        reply_markup=keyboard)
                except TelegramBadRequest:
                    pass
            await lobby_database.enter_lobby(lobby_id=callback_data.lobby_id,
                                             user_chat_id=str(callback.message.chat.id))
            await state.set_state(FSMLobbyClass.in_lobby)
            await state.update_data(lobby=callback_data.lobby_id, ready=0)
            bot_message = await callback.message.edit_text(text=lobby_message.return_message(user_name),
                                                           reply_markup=lobby_message.create_keyboard(user_name))
            await callback.answer(text='Вы зашли в лобби!')
            await users_database.update_game_page_message_id(chat_id=callback.message.chat.id,
                                                             message_id=bot_message.message_id)
        else:
            await callback.answer('Лобби не существует')
    else:
        await callback.answer('Лобби заполнено')


@router.callback_query(F.data == 'exit', StateFilter(FSMLobbyClass.in_lobby))
async def exit_command(callback: CallbackQuery,
                       state: FSMContext):
    data = await state.get_data()
    data_callback = callback.data
    data = update_previous_pages(data, data_callback)
    await exit_lobby(state=state, bot=bot, message=callback.message, data=data)
    lobby_pages = create_lobbies_page()
    keyboards = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby',
                                 back_button=data['previous_pages'][-1])
    await callback.answer(text='Вы вышли из лобби!')
    bot_message = await callback.message.edit_text(text='Список доступных лобби', reply_markup=keyboards)
    await users_database.update_lobbies_page_message_id(chat_id=callback.message.chat.id,
                                                        lobbies_page_message_id=bot_message.message_id)
    await state.set_state(FSMLobbyClass.select_lobby)
    data['previous_pages'].append(callback.data)
    if data.get('current_cards'):
        lobby_deck = lobby_database.get_lobby_deck(lobby_id=data['lobby']).split('~~~')
        user_cards = data['current_cards'].split('~~~')
        for card in user_cards:
            lobby_deck.append(card)
        await lobby_database.update_deck(deck='~~~'.join(lobby_deck))


@router.callback_query(F.data == 'ready', StateFilter(FSMLobbyClass.in_lobby))
async def ready_command_others(callback: CallbackQuery,
                               state: FSMContext):
    data = await state.get_data()
    if data['ready'] == 0:
        await state.update_data(ready=1)
        user_name = data['user_name']
        lobby_message = lobbies_messages_dict[data['lobby']]
        if games_messages_dict.get(data['lobby']):
            game_message = games_messages_dict[data['lobby']]
            game_message.add_user(callback.message.chat.id)
        else:
            deck = create_deck()
            game_message = GameMessage(users=[callback.message.chat.id],
                                       deck=deck,
                                       royal_card=' '.join(deck[-1].split('-')))
            games_messages_dict[data['lobby']] = game_message
        game_message.update_user_name(chat_id=callback.message.chat.id, user_name=user_name)
        game_message.give_next_cards_to_user(user_chat_id=callback.message.chat.id, value=6)
        lobby_message.update_ready_info(ready=1, user=user_name)
        storage = state.storage
        lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
        all_users_ready = lobby_message.get_all_users_ready()
        if all_users_ready:
            game_message.next_user()
            for chat_id in lobby_stat:
                await storage.set_state(StorageKey(bot_id=bot.id,
                                                   chat_id=int(chat_id),
                                                   user_id=int(chat_id)),
                                        state=FSMLobbyClass.in_game)
                await bot.edit_message_text(text='Игра началась!',
                                            chat_id=chat_id,
                                            message_id=users_database.get_user_game_page_message_id(
                                                chat_id=chat_id),
                                            reply_markup=None)
                await bot.send_message(text=str(game_message),
                                       chat_id=chat_id,
                                       reply_markup=game_message.create_game_keyboard(chat_id=int(chat_id)))
        else:
            for chat_id in lobby_stat:
                try:
                    user_name = lobby_message.return_message(users_database.get_user_name(chat_id))
                    await bot.edit_message_text(text=lobby_message.return_message(user_name),
                                                chat_id=chat_id,
                                                message_id=users_database.get_user_game_page_message_id(
                                                    chat_id=chat_id),
                                                reply_markup=lobby_message.create_keyboard(user_name))
                except TelegramBadRequest as e:
                    print(e)
    else:
        await callback.answer('Вы уже готовы!')


@router.callback_query(F.data == 'create_new_lobby', StateFilter(FSMLobbyClass.select_lobby))
async def create_new_lobby(callback: CallbackQuery,
                           state: FSMContext):
    data = await state.get_data()
    user_name = users_database.get_user_name(chat_id=callback.message.chat.id)
    lobby_id = lobby_database.create_new_lobby(user_chat_id=str(callback.message.chat.id))
    data['lobby'] = lobby_id
    data['ready'] = 0
    lobby_message = LobbyMessage([callback.message.chat.full_name])
    lobby_message.update_ready_info(ready=0, user=user_name)
    await state.set_state(FSMLobbyClass.in_lobby)
    await state.update_data(data=data)
    await users_database.delete_lobbies_page_message_id(chat_id=callback.message.chat.id)
    people_without_lobby = users_database.get_statistic_of_users_without_lobby()
    lobby_pages = create_lobbies_page()
    keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby', back_button='lobbies')
    for chat_id, message_id in people_without_lobby:
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                reply_markup=keyboard)
        except TelegramBadRequest:
            pass
    bot_message = await callback.message.edit_text(text=lobby_message.return_message(user_name),
                                                   reply_markup=lobby_message.create_keyboard(user_name))
    await callback.answer(text='Вы создали лобби!')
    await users_database.update_game_page_message_id(chat_id=callback.message.chat.id,
                                                     message_id=bot_message.message_id)
    lobbies_messages_dict[lobby_id] = lobby_message
