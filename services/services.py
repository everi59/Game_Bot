from aiogram import Bot
from aiogram.fsm.state import State, StatesGroup

from data.sql_database import LobbyDatabase
from keyboards.keyboards import LobbyCallbackFactory

lobby_database = LobbyDatabase('test6')


class FSMLobbyClass(StatesGroup):
    in_lobby = State()
    in_game = State()
    select_lobby = State()
    ready = State()
    lobby = State()
    current_cards = State()


def create_lobby_short_name(users):
    names = list(map(lambda x: x.split('-')[1], users))
    lobby_short_name = ', '.join(names)
    lobby_short_name.strip(', ')
    return lobby_short_name[:10]+'...' if len(lobby_short_name) > 12 else lobby_short_name


def create_lobbies_page():
    all_lobby_stat = lobby_database.get_all_lobby_stat()
    return {LobbyCallbackFactory(lobby_id=lobby[0]).pack():
            f"""{create_lobby_short_name(lobby[1].split('~~~'))} {len(lobby[1].split('~~~'))}/4"""
            for lobby in all_lobby_stat if lobby[1]}


async def send_messages_to_users(bot: Bot, message: str, users: list):
    for i in users:
        await bot.send_message(chat_id=int(i.split('-')[0]), text=message)


def get_lobby_members(pairs: list):
    members = list(map(lambda x: x.split('-')[1], pairs))
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
