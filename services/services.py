from aiogram import Bot
from aiogram.fsm.state import State, StatesGroup

from data.sql_database import LobbyDatabase
from keyboards.keyboards import LobbyCallbackFactory

lobby_database = LobbyDatabase('test6')


class FSMLobbyClass(StatesGroup):
    in_lobby = State()
    select_lobby = State()
    lobby = State()


def create_lobby_short_name(users):
    names = list(map(lambda x: x.split('-')[1], users))
    lobby_short_name = ', '.join(names)
    lobby_short_name.strip(', ')
    return lobby_short_name[:10]+'...' if len(lobby_short_name) < 10 else lobby_short_name


def create_lobbies_page():
    all_lobby_stat = lobby_database.get_all_lobby_stat()
    return {LobbyCallbackFactory(lobby_id=lobby[0]).pack():
            f"""{create_lobby_short_name(lobby[1].split())} {len(lobby[1].split())}/4"""
            for lobby in all_lobby_stat if lobby[1]}


async def send_messages_to_users(bot: Bot, message: str, users: list):
    for i in users:
        await bot.send_message(chat_id=int(i.split('-')[0]), text=message)


def get_lobby_members(pairs: list):
    members = list(map(lambda x: x.split('-')[1], pairs))
    return '\n'.join(members)
