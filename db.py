import sqlite3

# Потокобезопасное подключение. Не открываем соединение в каждой функции, только в декораторе

def ensure_connection(function):

    def wrapper(*args, **kwargs):

        with sqlite3.connect('vault.db') as conn:
            res = function(*args, conn=conn, **kwargs)

        return res

    return wrapper


# Флаг force удаляет таблицу, если существует. Если сразу запустить код с этим флагом, он не упадет.

@ensure_connection

def init_db(conn, force: bool = False):
    ''':param force: явно пересоздать все таблицы'''

    c = conn.cursor()

    if force:
        c.execute('DROP TABLE IF EXISTS user_data') 
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            id              INTEGER PRIMARY KEY,
            message         TEXT,
            user_id         INTEGER,
            actual_name     TEXT,
            admins_msg_id   TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_hashtags (
            id              INTEGER PRIMARY KEY,
            hashtags        TEXT
        )
    ''')

    c.execute('SELECT hashtags FROM admin_hashtags WHERE id=1')
    result = c.fetchone()

    if result is None:

        insert = 'Готово'
        c.execute('INSERT INTO admin_hashtags (hashtags) VALUES (?)', (insert, ))

    conn.commit()


@ensure_connection

def register_questions(conn, user_id, message, actual_name, admins_msg_id):

    c = conn.cursor()
    c.execute('INSERT INTO user_data (user_id, message, actual_name, admins_msg_id) VALUES (?, ?, ?, ?)', (user_id, message, actual_name, admins_msg_id))
    conn.commit()


@ensure_connection

def fetch_messages_from_same_user(conn, actual_name):

    c = conn.cursor()
    c.execute('SELECT admins_msg_id FROM user_data WHERE actual_name=?', (actual_name, ))
    result_1 = c.fetchall()
    c.execute('SELECT message FROM user_data WHERE actual_name=?', (actual_name, ))
    result_2 = c.fetchall()
    c.execute('SELECT user_id FROM user_data WHERE actual_name=?', (actual_name, ))
    result_3 = c.fetchone()
    c.execute('DELETE FROM user_data WHERE actual_name=?', (actual_name, ))
    conn.commit()

    return result_1, result_2, result_3


@ensure_connection

def delete_message_by_id(conn, admins_msg_id):

    c = conn.cursor()
    c.execute('DELETE FROM user_data WHERE admins_msg_id=?', (admins_msg_id, ))
    conn.commit()


@ensure_connection

def find_user_by_msg_id(conn, admins_msg_id):

    c = conn.cursor()
    c.execute('SELECT user_id FROM user_data WHERE admins_msg_id=?', (admins_msg_id, ))
    result = c.fetchone()
    c.execute('DELETE FROM user_data WHERE admins_msg_id=?', (admins_msg_id, ))
    conn.commit()

    return result


@ensure_connection

def add_to_hashtag_list(conn, hashtag):

    c = conn.cursor()

    c.execute('SELECT hashtags FROM admin_hashtags')

    result = c.fetchall()
    parseable = [each for tuple in result for each in tuple]
    count = len(parseable)


    if hashtag in parseable:

        return False, count
    
    else:

        c.execute('INSERT INTO admin_hashtags (hashtags) VALUES (?)', (hashtag, ))

        conn.commit()

        return True, count


@ensure_connection

def delete_hashtag_from_list(conn, hashtag):

    c = conn.cursor()

    c.execute('SELECT hashtags FROM admin_hashtags WHERE hashtags=?', (hashtag, ))
    result = c.fetchone()

    if result is None:

        return False

    else:

        c.execute('DELETE FROM admin_hashtags WHERE hashtags=?', (hashtag, ))
        conn.commit()

        return True

@ensure_connection

def parse_hashtags(conn):

    c = conn.cursor()
    
    c.execute('SELECT hashtags FROM admin_hashtags')
    
    result = c.fetchall()
    parseable = [each for tuple in result for each in tuple]

    return parseable