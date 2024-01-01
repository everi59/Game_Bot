from aiogram import Bot
from aiogram.fsm.state import State, StatesGroup

from data.sql_database import LobbyDatabase
from keyboards.keyboards import LobbyCallbackFactory

lobby_database = LobbyDatabase('test6')


class FSMLobbyClass(StatesGroup):
    in_lobby = State()
    select_lobby = State()
    lobby = State()


def create_lobbies_page():
    return {LobbyCallbackFactory(lobby_id=i).pack(): f'Лобби №{i} {len(lobby_database.get_lobby_stat(i))}/4' for i in range(1, 5)}


async def send_messages_to_users(bot: Bot, message: str, users: list):
    for i in users:
        await bot.send_message(chat_id=int(i), text=message)


