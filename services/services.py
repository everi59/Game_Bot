from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import InlineKeyboardMarkup, Message
from bot import users_database, lobby_database
from keyboards.keyboards import LobbyCallbackFactory, create_inline_kb, CardsCallbackFactory


class FSMLobbyClass(StatesGroup):
    select_lobby = State()
    in_lobby = State()
    in_game = State()
    ready = State()
    lobby = State()
    current_cards = State()
    previous_pages = State()
    lobby_message = State()
    game_message_id = State()


def create_user_list_for_lobby(users: list, ready_dict: dict):
    users_list_for_lobby = (
        '\n'.join([f'{i}. {users[i-1]} - {"Готов" if ready_dict[users[i-1]] else "Не готов"}' if i <= len(users) else
                   f'{i}. Ждем игрока' for i in range(1, 5)]))
    return users_list_for_lobby


def create_lobby_short_name(users):
    names = list(map(lambda x: users_database.get_user_name(x), users))
    lobby_short_name = ', '.join(names)
    return lobby_short_name[:10]+'...' if len(lobby_short_name) > 12 else lobby_short_name


def create_game_keyboard_dict(cards: list):
    return {CardsCallbackFactory(face=card.split('-')[0], color=card.split('-')[1]):
            f'{" ".join(card.split("-"))}' for card in cards}


def create_lobbies_page():
    all_lobby_stat = lobby_database.get_all_lobby_stat()
    return {LobbyCallbackFactory(lobby_id=lobby[0]).pack():
            f"""{create_lobby_short_name(lobby[1].split('~~~'))} {len(lobby[1].split('~~~'))}/4"""
            for lobby in all_lobby_stat if lobby[1]}


async def send_messages_to_users(bot: Bot, message: str, users: list, markup: Optional[InlineKeyboardMarkup]):
    for i in users:
        await bot.send_message(chat_id=int(i), text=message, reply_markup=markup)


async def edit_users_messages(bot: Bot, message: str, users: list, markup: Optional[InlineKeyboardMarkup]):
    for i in users:
        await bot.edit_message_text(chat_id=int(i), text=message, reply_markup=markup)


def get_lobby_members(users_ids: list):
    members = list(map(lambda user_id:  users_database.get_user_name(user_id), users_ids))
    return '\n'.join(members)


def create_deck():
    faces = list(range(6, 11))
    [faces.append(i) for i in ["Король", "Дама", "Валет", "Туз"]]
    colour = ["♥️", "♦️", "♣️", "♠️"]
    from itertools import product
    from random import shuffle
    deck = ["{}-{}".format(*card) for card in product(faces, colour)]
    shuffle(deck)
    return '~~~'.join(deck)


def get_next_cards(deck, cards_num):
    deck = deck.split('~~~')
    return [deck[:cards_num], deck[cards_num:]]


class LobbyMessage:
    ready_text = 'Вы не готовы!\n\n'
    lobby_keyboard_buttons = {'ready': 'Приготовиться', 'exit': 'Выйти'}
    keyboard = create_inline_kb(dct=lobby_keyboard_buttons, width=1)
    ready_dict = {}

    def __init__(self, users: list):
        self.users = users

    def __str__(self):
        users_list = create_user_list_for_lobby(users=self.users, ready_dict=self.ready_dict)
        lobby_text = self.ready_text + f'Участники лобби:\n{users_list}'
        return lobby_text

    def delete_user(self, user: str):
        self.users.remove(user)
        self.ready_dict.pop(user)

    def add_user(self, user: str):
        self.users.append(user)

    def update_ready_info(self, ready: int, user: str):
        self.ready_dict[user] = ready
        if ready == 1:
            self.lobby_keyboard_buttons = {'exit': 'Выйти'}
            self.keyboard = create_inline_kb(dct=self.lobby_keyboard_buttons, width=1)
            self.ready_text = 'Вы готовы! \nОжидаем других игроков!\n\n'
        else:
            self.lobby_keyboard_buttons = {'ready': 'Приготовиться', 'exit': 'Выйти'}
            self.keyboard = create_inline_kb(dct=self.lobby_keyboard_buttons, width=1)
            self.ready_text = 'Вы не готовы!\n\n'

    def get_all_users_ready(self):
        values = self.ready_dict.values()
        return all(values) and len(values) == 4


class GameMessage:
    def __init__(self, users: list, deck: list, royal_card: str):
        self.users = users
        self.deck = deck
        self.royal_card = royal_card

    cards_on_table = []
    user_from_index = 0
    user_to_index = 1
    user_from = 0
    user_to = 0
    users_cards = {}
    users_wined = []
    user_from_bito = 0

    def next_user(self):
        self.user_from = self.users[self.user_from_index]
        self.user_to = self.users[self.user_to_index]
        self.user_from_index = (self.user_from_index + 1) % 4
        self.user_to_index = (self.user_to_index + 1) % 4

    def update_user_cards(self, user_chat_id: int, user_cards: list):
        self.users_cards[user_chat_id] = user_cards

    def delete_user_card(self, card: str, user_chat_id: int):
        cards = self.users_cards[user_chat_id]
        cards.remove(card)
        self.users_cards[user_chat_id] = cards

    def create_game_keyboard(self, chat_id: int):
        if self.user_from == chat_id:
            dct = create_game_keyboard_dict(self.users_cards[chat_id])
            if self.cards_on_table:
                return create_inline_kb(width=1, dct=dct, last_btn='bito', back_button='exit')
            else:
                return create_inline_kb(width=1, dct=dct, back_button='exit')
        if self.user_to == chat_id:
            dct = create_game_keyboard_dict(self.users_cards[chat_id])
            if self.cards_on_table:
                return create_inline_kb(width=1, dct=dct, last_btn='beru', back_button='exit')
            else:
                return create_inline_kb(width=1, dct={'exit': 'Выйти'}, back_button='exit')
        if self.user_from_bito:
            dct = create_game_keyboard_dict(self.users_cards[chat_id])
            return create_inline_kb(width=1, dct=dct, last_btn='bito', back_button='exit')
        return create_inline_kb(width=1, back_button='exit')


async def exit_lobby(state: FSMContext, data, bot, message: Message):
    await state.update_data(lobby=None)
    await lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id))
    lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
    storage = state.storage
    if lobby_stat[0] == '':
        await lobby_database.delete_lobby(data['lobby'])
    else:
        for chat_id in lobby_stat:
            try:
                storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
                                                                 chat_id=int(chat_id),
                                                                 user_id=int(chat_id)))
                lobby_message = storage_data['lobby_message']
                lobby_message.delete_user(users_database.get_user_name(chat_id=chat_id))
                await bot.edit_message_text(text=str(lobby_message), chat_id=chat_id,
                                            message_id=users_database.get_user_game_page_message_id(
                                                chat_id=message.chat.id),
                                            reply_markup=lobby_message.keyboard)
            except TelegramBadRequest:
                pass
    lobby_pages = create_lobbies_page()
    keyboard = create_inline_kb(width=2, dct=lobby_pages)
    people_without_lobby = users_database.get_statistic_of_users_without_lobby()
    for chat_id, message_id in people_without_lobby:
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                reply_markup=keyboard)
        except TelegramBadRequest:
            pass


def update_previous_pages(data, callback_data):
    if callback_data in data['previous_pages']:
        data['previous_pages'] = data['previous_pages'][:-2]
    return data
