import psycopg2

conn = psycopg2.connect(host='localhost', dbname='postgres', user='postgres', password='1234', port=5432)


class LobbyDatabase:
    def __init__(self, name):
        self.name = name

    async def create_table(self):
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.name}
            (lobby_id BIGSERIAL PRIMARY KEY,
            users TEXT);
            """)
        conn.commit()
        cur.close()
        print('[INFO] TABLE CREATED SUCCESSFULLY')

    async def enter_lobby(self, lobby_id: int, user_chat_id: str):
        cur = conn.cursor()
        cur.execute(f"""SELECT users FROM {self.name}
                        WHERE lobby_id={lobby_id};
                        """)
        users = cur.fetchone()[0].split('~~~')
        users.append(f"""{user_chat_id}""")
        cur.execute(f"""UPDATE {self.name} SET users='{'~~~'.join(users)}' WHERE lobby_id={lobby_id};""")
        conn.commit()
        cur.close()

    async def exit_lobby(self, lobby_id: int, user_chat_id: str):
        cur = conn.cursor()
        cur.execute(f"""SELECT users FROM {self.name}
                                WHERE lobby_id={lobby_id};
                                """)
        users = cur.fetchone()[0].split('~~~')
        users.remove(f"""{user_chat_id}""")
        cur.execute(f"""UPDATE {self.name} SET users='{'~~~'.join(users)}' WHERE lobby_id={lobby_id};""")
        conn.commit()
        cur.close()

    def get_lobby_stat(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""SELECT users FROM {self.name}
                    WHERE lobby_id={lobby_id};""")
        s = cur.fetchone()[0].split('~~~')
        conn.commit()
        cur.close()
        return s

    def create_new_lobby(self, user_chat_id: str):
        cur = conn.cursor()
        cur.execute(f"""INSERT INTO {self.name} (users) VALUES ('{user_chat_id}')""")
        cur.execute(f"""SELECT lobby_id FROM {self.name}
                        WHERE users='{user_chat_id}';""")
        lobby_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return lobby_id

    def get_all_lobby_stat(self):
        cur = conn.cursor()
        cur.execute(f"""SELECT lobby_id, users FROM {self.name}""")
        all_lobby_stat = cur.fetchall()
        return all_lobby_stat

    async def delete_lobby(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""DELETE FROM {self.name} WHERE lobby_id={lobby_id};""")
        conn.commit()
        cur.close()


class UsersDatabase:
    def __init__(self, name):
        self.name = name

    async def create_table(self):
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.name}
            (chat_id BIGINT PRIMARY KEY,
            user_name TEXT,
            lobbies_page_message_id BIGINT,
            game_page_message_id BIGINT,
            balance INT,
            games_amount INT,
            wines_amount INT,
            loses_amount INT,
            last_free_reward_date_timestamp INT);""")
        conn.commit()
        cur.close()
        print('[INFO] TABLE CREATED SUCCESSFULLY')

    async def insert_new_user(self, chat_id: int, user_name: str):
        cur = conn.cursor()
        cur.execute(f"""INSERT INTO {self.name}
                        (chat_id, user_name, lobbies_page_message_id, games_amount, wines_amount, loses_amount, balance,
                        last_free_reward_date_timestamp)
                        VALUES ({chat_id}, '{user_name}', NULL, 0, 0, 0, 1000, 0)
                        ON CONFLICT (chat_id) DO NOTHING;
                        """)
        conn.commit()
        cur.close()

    def get_statistic_of_users_without_lobby(self):
        cur = conn.cursor()
        cur.execute(f"""SELECT chat_id, lobbies_page_message_id FROM {self.name}
         WHERE lobbies_page_message_id IS NOT NULL;""")
        stat = cur.fetchall()
        conn.commit()
        cur.close()
        return stat

    def get_user_name(self, chat_id: int):
        cur = conn.cursor()
        cur.execute(f"""SELECT user_name FROM {self.name} WHERE chat_id={chat_id}""")
        user_name = cur.fetchone()
        conn.commit()
        cur.close()
        return user_name[0]

    async def update_lobbies_page_message_id(self, chat_id: int, lobbies_page_message_id: int):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET lobbies_page_message_id={lobbies_page_message_id}
         WHERE chat_id={chat_id};""")
        conn.commit()
        cur.close()

    async def delete_lobbies_page_message_id(self, chat_id: int):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET lobbies_page_message_id=NULL WHERE chat_id={chat_id};""")
        conn.commit()
        cur.close()

    def get_user_statistic(self, chat_id):
        cur = conn.cursor()
        cur.execute(f"""SELECT user_name, balance, games_amount, wines_amount, loses_amount
        FROM {self.name} WHERE chat_id={chat_id}""")
        stat = cur.fetchall()
        conn.commit()
        cur.close()
        return stat[0]

    def get_user_balance(self, chat_id):
        cur = conn.cursor()
        cur.execute(f"""SELECT balance FROM {self.name} WHERE chat_id={chat_id}""")
        balance = cur.fetchone()
        conn.commit()
        cur.close()
        return balance[0]

    def update_user_balance(self, chat_id: int, balance: int):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET balance={balance} WHERE chat_id={chat_id};""")
        conn.commit()
        cur.close()

    async def update_game_page_message_id(self, chat_id, message_id):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET game_page_message_id={message_id} WHERE chat_id={chat_id};""")
        conn.commit()
        cur.close()

    def get_user_game_page_message_id(self, chat_id: int):
        cur = conn.cursor()
        cur.execute(f"""SELECT game_page_message_id FROM {self.name} WHERE chat_id={chat_id}""")
        page_message_id = cur.fetchone()
        conn.commit()
        cur.close()
        return page_message_id[0]

    def get_last_free_reward_date_timestamp(self, chat_id: int):
        cur = conn.cursor()
        cur.execute(f"""SELECT last_free_reward_date_timestamp FROM {self.name} WHERE chat_id={chat_id}""")
        last_free_reward_date_timestamp = cur.fetchone()
        conn.commit()
        cur.close()
        return last_free_reward_date_timestamp[0]

    def update_last_free_reward_date_timestamp(self, chat_id: int, last_free_reward_date_timestamp: int):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET last_free_reward_date_timestamp={last_free_reward_date_timestamp}
         WHERE chat_id={chat_id}""")
        conn.commit()
        cur.close()
