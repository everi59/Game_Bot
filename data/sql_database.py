import sqlite3

conn = sqlite3.connect('test.py')


class LobbyDatabase:
    def __init__(self, name):
        self.name = name

    def create_table(self):
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {self.name}
           (id INT PRIMARY KEY,
           people TEXT);""")
        conn.commit()
        cur.close()
        print('[INFO] TABLE CREATED SUCCESSFULLY')

    def default_lobby(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""INSERT OR IGNORE INTO {self.name} (id, people)
        VALUES ({lobby_id}, '');
        """)
        conn.commit()
        cur.close()

    def enter_lobby(self, lobby_id: int, user_chat_id: str):
        cur = conn.cursor()
        cur.execute(f"""SELECT people FROM {self.name}
                        WHERE id={lobby_id};
                        """)
        s = cur.fetchone()[0].split()
        s.append(user_chat_id)
        cur.execute(f"""UPDATE {self.name} SET people='{' '.join(s)}' WHERE id={lobby_id};""")
        conn.commit()
        cur.close()

    def exit_lobby(self, lobby_id: int, user_chat_id: str):
        cur = conn.cursor()
        cur.execute(f"""SELECT people FROM {self.name}
                                WHERE id={lobby_id};
                                """)
        s = cur.fetchone()[0].split()
        s.remove(user_chat_id)
        cur.execute(f"""UPDATE {self.name} SET people='{' '.join(s)}' WHERE id={lobby_id};""")
        conn.commit()
        cur.close()

    def reset_lobby(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""UPDATE {self.name} SET people='' WHERE id={lobby_id};""")
        conn.commit()
        cur.close()

    def get_lobby_stat(self, lobby_id: int):
        cur = conn.cursor()
        cur.execute(f"""SELECT people FROM {self.name}
                                        WHERE id={lobby_id};
                                        """)
        s = cur.fetchone()[0].split()
        conn.commit()
        cur.close()
        return s
