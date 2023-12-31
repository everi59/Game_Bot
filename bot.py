import logging
import asyncio

from aiogram import Bot, Dispatcher
from config.config import Config, load_config
from handlers import user_handlers
from data.sql_database import LobbyDatabase
from services.set_menu import set_main_menu

logger = logging.getLogger(__name__)
lobby_database = LobbyDatabase('test3')
config: Config = load_config()
bot = Bot(token=config.tg_bot.token,
          parse_mode='HTML')


async def main():
    lobby_database.create_table()
    for i in range(1, 5):
        lobby_database.reset_lobby(i)
        lobby_database.default_lobby(i)
    lobby_database.reset_lobby(-1)
    lobby_database.default_lobby(-1)
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