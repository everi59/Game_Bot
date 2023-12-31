from aiogram.fsm.state import State, StatesGroup

from data.sql_database import LobbyDatabase
from keyboards.keyboards import LobbyCallbackFactory

lobby_database = LobbyDatabase('test3')


class FSMLobbyClass(StatesGroup):
    in_lobby = State()
    select_lobby = State()
    lobby = State()


def create_lobbies_page():
    return {LobbyCallbackFactory(lobby_id=i).pack(): f'Лобби №{i} {len(lobby_database.get_lobby_stat(i))}/4' for i in range(1, 5)}
