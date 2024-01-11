from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import InlineKeyboardMarkup, Message
from bot import users_database, lobby_database
from keyboards.keyboards import LobbyCallbackFactory, create_inline_kb, CardsCallbackFactory


lobbies_messages_dict = {}
games_messages_dict = {}


class FSMLobbyClass(StatesGroup):
    select_lobby = State()
    in_lobby = State()
    in_game = State()
    ready = State()
    lobby = State()
    current_cards = State()
    previous_pages = State()
    user_name = State()


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
    return deck


class LobbyMessage:
    ready_text = 'Вы готовы!\n\n'
    unready_text = 'Вы не готовы!\n\n'
    ready_dict = {}

    def __init__(self, users: list):
        self.users = users

    def return_message(self, user: str):
        users_list = create_user_list_for_lobby(users=self.users, ready_dict=self.ready_dict)
        lobby_text = (self.ready_text if self.ready_dict.get(user) else self.unready_text) + (f'Участники лобби:\n'
                                                                                              f'{users_list}')
        return lobby_text

    def delete_user(self, user: str):
        self.users.remove(user)
        self.ready_dict.pop(user)

    def add_user(self, user: str):
        self.users.append(user)

    def update_ready_info(self, ready: int, user: str):
        self.ready_dict[user] = ready

    def get_all_users_ready(self):
        values = self.ready_dict.values()
        return all(values) and len(values) == 2

    def create_keyboard(self, user: str):
        if self.ready_dict.get(user) == 1:
            return create_inline_kb(dct={'exit': 'Выйти'}, width=1)
        else:
            return create_inline_kb(dct={'ready': 'Приготовиться', 'exit': 'Выйти'}, width=1)


class GameMessage:
    def __init__(self, users: list, deck: list, royal_card: str):
        self.users = users
        self.deck = deck
        self.royal_card = royal_card

    game_text = ('Ходит игрок: {}\n'
                 'Кроется игрок: {}\n\n'
                 'Карт в колоде: {}\n'
                 'Козырная карта: {}\n')
    cards_on_table_text = 'Карты на столе:\n'
    users_text = 'Игроки:\n'

    def __str__(self):
        user_from = self.users_names[self.user_from]
        user_to = self.users_names[self.user_to]
        cards_value = len(self.deck)
        royal_card = self.royal_card
        return self.game_text.format(user_from, user_to, cards_value, royal_card)

    cards_on_table = {}
    user_from_index = 0
    user_to_index = 1
    user_from = 0
    user_to = 0
    users_cards = {}
    users_wined = []
    user_from_bito = False
    users_names = {}

    def next_user(self):
        self.user_from = self.users[self.user_from_index]
        self.user_to = self.users[self.user_to_index]
        self.user_from_index = (self.user_from_index + 1) % 4
        self.user_to_index = (self.user_to_index + 1) % 4

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

    def give_next_cards_to_user(self, user_chat_id: int, value: int):
        if self.users_cards.get(user_chat_id):
            if len(self.deck) <= value:
                self.users_cards[user_chat_id].extend(self.deck)
                self.deck = []
            else:
                self.users_cards[user_chat_id].extend(self.deck[:value])
                self.deck = self.deck[value:]
        else:
            if len(self.deck) <= value:
                self.users_cards[user_chat_id] = self.deck
                self.deck = []
            else:
                self.users_cards[user_chat_id] = self.deck[:value]
                self.deck = self.deck[value:]

    def update_user_name(self, chat_id: int, user_name: str):
        self.users_names[chat_id] = user_name

    def add_user(self, user_chat_id: int):
        self.users.append(user_chat_id)


async def exit_lobby(state: FSMContext, data, bot, message: Message):
    await state.update_data(lobby=None)
    await lobby_database.exit_lobby(lobby_id=data['lobby'], user_chat_id=str(message.chat.id))
    lobby_stat = lobby_database.get_lobby_stat(data['lobby'])
    if lobby_stat[0] == '':
        await lobby_database.delete_lobby(data['lobby'])
    else:
        lobby_message = lobbies_messages_dict.get(data['lobby'])
        lobby_message.delete_user(data['user_name'])
        for chat_id in lobby_stat:
            try:
                await bot.edit_message_text(text=str(lobby_message), chat_id=chat_id,
                                            message_id=users_database.get_user_game_page_message_id(
                                                chat_id=message.chat.id),
                                            reply_markup=lobby_message.keyboard)
            except TelegramBadRequest:
                pass
    lobby_pages = create_lobbies_page()
    storage = state.storage
    people_without_lobby = users_database.get_statistic_of_users_without_lobby()
    for chat_id, message_id in people_without_lobby:
        try:
            storage_data = await storage.get_data(StorageKey(bot_id=bot.id,
                                                             chat_id=int(chat_id),
                                                             user_id=int(chat_id)))
            keyboard = create_inline_kb(width=2, dct=lobby_pages, last_btn='create_new_lobby',
                                        back_button=storage_data['previous_pages'][-1])
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
                                                reply_markup=keyboard)
        except TelegramBadRequest:
            pass


def update_previous_pages(data, callback_data):
    if callback_data in data['previous_pages']:
        data['previous_pages'] = data['previous_pages'][:-2]
    return data
