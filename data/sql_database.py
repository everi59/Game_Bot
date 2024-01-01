import sqlite3

conn = sqlite3.connect('test1.py')


class LobbyDatabase:
    def __init__(self, name):
        self.name = name

    def create_table(self):
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.name}
            (lobby_id INT PRIMARY KEY,
            users TEXT);
            """)
        conn.commit()
        cur.close()
        print('[INFO] TABLE CREATED SUCCESSFULLY')

    def default_lobby(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""INSERT OR IGNORE INTO {self.name} (lobby_id, users)
        VALUES ({lobby_id}, '');
        """)
        conn.commit()
        cur.close()

    def enter_lobby(self, lobby_id: int, user_chat_id: str, user_name: str):
        cur = conn.cursor()
        cur.execute(f"""SELECT users FROM {self.name}
                        WHERE lobby_id={lobby_id};
                        """)
        pairs = cur.fetchone()[0].split()
        pairs.append(f"""{user_chat_id}-{user_name}""")
        cur.execute(f"""UPDATE {self.name} SET users='{' '.join(pairs)}' WHERE lobby_id={lobby_id};""")
        conn.commit()
        cur.close()

    def exit_lobby(self, lobby_id: int, user_chat_id: str, user_name: str):
        cur = conn.cursor()
        cur.execute(f"""SELECT users FROM {self.name}
                                WHERE lobby_id={lobby_id};
                                """)
        pairs = cur.fetchone()[0].split()
        pairs.remove(f"""{user_chat_id}-{user_name}""")
        cur.execute(f"""UPDATE {self.name} SET users='{' '.join(pairs)}' WHERE lobby_id={lobby_id};""")
        conn.commit()
        cur.close()

    def reset_lobby(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET users='' WHERE lobby_id={lobby_id};""")
        conn.commit()
        cur.close()

    def get_lobby_stat(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""SELECT users FROM {self.name}
                    WHERE lobby_id={lobby_id};""")
        s = cur.fetchone()[0].split()
        conn.commit()
        cur.close()
        return s


class UsersWithoutLobbiesDatabase:
    def __init__(self, name):
        self.name = name

    def create_table(self):
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.name}
            (chat_id INT PRIMARY KEY,
            message_id INT);""")
        conn.commit()
        cur.close()
        print('[INFO] TABLE CREATED SUCCESSFULLY')

    def insert_users_message_id(self, chat_id, message_id):
        cur = conn.cursor()
        cur.execute(f"""INSERT OR IGNORE INTO {self.name} (chat_id, message_id)
                VALUES ({chat_id}, {message_id});
                """)
        conn.commit()
        cur.close()

    def update_users_message_id(self, chat_id, message_id):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET message_id='{message_id}' WHERE chat_id={chat_id};""")
        conn.commit()
        cur.close()

    def get_statistic_of_users(self):
        cur = conn.cursor()
        cur.execute(f"""SELECT chat_id, message_id FROM {self.name}""")
        stat = cur.fetchall()
        conn.commit()
        cur.close()
        return stat

    def delete_chat_id(self, chat_id):
        cur = conn.cursor()
        cur.execute(f"""DELETE FROM {self.name} WHERE chat_id={chat_id};""")
        conn.commit()
        cur.close()