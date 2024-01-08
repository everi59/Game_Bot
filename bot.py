import logging
import asyncio

from aiogram import Bot, Dispatcher

from config.config import Config, load_config
from handlers import user_handlers
from data.sql_database import LobbyDatabase, UsersDatabase
from services.set_menu import set_main_menu


logger = logging.getLogger(__name__)
lobby_database = LobbyDatabase('test6')
users_database = UsersDatabase('test5')
config: Config = load_config()
bot = Bot(token=config.tg_bot.token,
          parse_mode='HTML')


async def main():
    await lobby_database.create_table()
    await users_database.create_table()
    lobbies_id = lobby_database.get_all_lobby_stat()
    for i in lobbies_id:
        await lobby_database.delete_lobby(lobby_id=i[0])
    logging.basicConfig(level=logging.INFO,
                        format='%(filename)s:%(lineno)d #%(levelname)-8s '
                               '[%(asctime)s] - %(name)s - %(message)s')
    logger.info('Starting bot')

    dp = Dispatcher()

    dp.include_router(user_handlers.router)
    # dp.include_router(other_handlers.router)

    await set_main_menu(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
