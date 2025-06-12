import psycopg2
import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = '7670973361:AAGPy486i_aCQpTl7BrzzquwEruFqIs06iY'
bot = TeleBot(token_bot, state_storage=state_storage)

# Подключаемся к базе данных
conn = psycopg2.connect(database = "tg", user = 'postgres', password = '000')
cursor = conn.cursor()

# Создаем таблицу, если ее еще нет
# Таблица пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS users  (
    id SERIAL PRIMARY KEY,            -- уникальный ID записи (автоинкремент)
    user_id BIGINT UNIQUE NOT NULL,   -- уникальный ID пользователя в мессенджере
    name VARCHAR(100),                -- имя пользователя (опционально)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# Таблица глобальных слов (общий словарь)
cursor.execute('''
CREATE TABLE IF NOT EXISTS words (
    word_id SERIAL PRIMARY KEY,
    word VARCHAR(50) NOT NULL,        -- слово
    translation VARCHAR(50) NOT NULL, -- перевод
    is_global BOOLEAN DEFAULT TRUE   -- глобальное слово
);
''')

# Таблица персональных слов конкретных пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_custom_words (
    word_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,          -- ссылка на пользователя
    word VARCHAR(50) NOT NULL,        -- слово
    translation VARCHAR(50) NOT NULL, -- перевод
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
''')

# Добавляем пример данных
cursor.execute("SELECT COUNT(*) FROM words")
count = cursor.fetchone()[0]
if count is None:
    # Таблица не существует или возникла ошибка
    print("Ошибка: таблица 'words' отсутствует или пуста.")
else:
    if count == 0:
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Peace', 'Мир', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Hello', 'Привет', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Put', 'Класть', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Car', 'Машина', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Black', 'Черный', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Yellow', 'Желтый', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Fine', 'Прекрасно', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Who', 'Кто', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('What', 'Что', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Where', 'Где', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Try', 'Пробовать', 'true');")
        cursor.execute("INSERT INTO words (word, translation, is_global) VALUES ('Exit', 'Выход', 'true');")

conn.commit()
cursor.close()


known_users = []
userStep = {}
buttons = []
user_state = {}


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


# Функция для получения ID следующего слова
def get_next_word_id(cid):
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM (
        (
          SELECT w.word_id, w.word, w.translation
          FROM words w
          WHERE w.is_global = true
        )
        UNION ALL
        (
          SELECT ucw.word_id, ucw.word, ucw.translation
          FROM user_custom_words ucw
          WHERE ucw.user_id = %s
          AND ucw.word IS NOT NULL
        )
    ) AS combined
    ORDER BY RANDOM()
    LIMIT 1;''',(cid,))
    row = cursor.fetchone()
    print(row)
    cursor.close()
    return row if row else None


# Функция для загрузки пользователя в словарь
def start():
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, name FROM users')
    res = cursor.fetchall()
    for line in res:
        known_users.append({'cid': line[0], 'name': line[1]})
    print('Start', known_users)

# Функция для добавления пользователя
def add_user(cid, name=""):
    p  = {}
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = %s', (cid,))
    row = cursor.fetchone()
    if row[0] == 0:
        cursor.execute('INSERT INTO users (user_id, name) VALUES (%s, %s)', (cid, name))
        conn.commit()
        p['cid'] = cid
        p['name'] = name
        known_users.extend(p)
        print('Добавлен новый пользователь', name)
    cursor.close()
    return True

#Функция для проверки наличия пользователя
def test_cid(cid):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = %s', (cid,))
    row = cursor.fetchone()
    if row[0] != 0:
        return True
    return False

# Функция для добавления пользователя
def get_name_by_cid(cid):
    for user in known_users:
        if user['cid'] == cid:
            return user['name']
    return None  # если не найдено

# Функция для получения имени пользователя
def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0

# Функция для создания списка дополнительных слов
def other_cards(cid):
    cursor = conn.cursor()
    other_words = []
    cursor.execute('''
    SELECT * FROM (
        (
          SELECT w.word, w.translation
          FROM words w
          WHERE w.is_global = true
        )
        UNION ALL
        (
          SELECT ucw.word, ucw.translation
          FROM user_custom_words ucw
          WHERE ucw.user_id = %s
          AND ucw.word IS NOT NULL
        )
    ) AS combined
    ORDER BY RANDOM()
    LIMIT 4;
    ''', (cid,))
    rows = cursor.fetchall()
    cursor.close()
    for line in rows:
        if line[0]:
            other_words.append(line[0])
    return other_words

# Функция для удаления пользовательского слова
def del_word(word):
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM user_custom_words WHERE word = %s', (word,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при удалении слова: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

# Функция для добавления пользовательского слова
def add_new_word(cid, new_word, translation):
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO user_custom_words (user_id, word, translation) VALUES (%s, %s, %s);",
            (cid, new_word, translation))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при добавлении слова: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

#----------------------------------------------------------------------------------------------

@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    start()
    if not test_cid(cid):
        bot.send_message(cid, "Hello, stranger, let study English...")
        bot.send_message(cid, "Type your name...")
        userStep[cid] = 9
        print('Add name', userStep)
    else:
        bot.send_message(cid, f"Hello, {get_name_by_cid(cid)}")
        next_cards(message)

#-------------------------------------------------------------------------------------------------------

@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 9)
def save_new_name(message):
    cid = message.chat.id
    text = message.text.strip()
    add_user(cid, text)
    bot.send_message(cid, f"Hello, {text}")
    userStep[cid] = 0
    markup = types.ReplyKeyboardMarkup(row_width=2)

    # Получаем первое слово
    word_id, word, translate_word = get_next_word_id(cid)
    print('Start_word', word_id, word, translate_word)

    # создание клавиатуры
    target_word = word
    buttons.clear()
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    other_words = other_cards(cid)
    print(other_words)
    # удаление слова если оно есть из списка предлагаемых
    if target_word in other_words:
        other_words.remove(target_word)
    else:
        del other_words[0]
    other_words_btn = [types.KeyboardButton(word) for word in other_words]
    buttons.extend(other_words_btn)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate_word}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate_word
        data['other_words'] = other_words
    print('After new name userStep', userStep)

#--------------------------------------------------------------------------------------------------------

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    cid = message.chat.id
    word_id, word, translate_word = get_next_word_id(cid)
    print('Start_word', word_id, word, translate_word)
    # Создаем новую клавиатуру
    markup = types.ReplyKeyboardMarkup(row_width=2)

    # подготовка кнопок
    target_word = word
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate_word
    print('Data1', data)
    other_words = other_cards(cid)
    if target_word in other_words:
        other_words.remove(target_word)
    else:
        del other_words[0]
    buttons.clear()

    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    other_words_btn = [types.KeyboardButton(word) for word in other_words]
    buttons.extend(other_words_btn)

    random.shuffle(buttons)

    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)

    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)

    bot.send_message(message.chat.id, f"Выберите перевод:\n🇷🇺 {translate_word}", reply_markup=markup)

#---------------------------------------------------------------------------------------------------------

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    # Получаем текущее слово, отображаемое для пользователя
    with bot.retrieve_data(message.from_user.id, cid) as data:
        target_word = data.get('target_word')
    print('Data2', data)
    if not target_word:
        bot.send_message(cid, "Нет слова для удаления.")
        return

    else:
        if del_word(target_word):
            bot.send_message(cid, f"Слово {target_word} удалено.")
            print('Delete', target_word)
        else:
            bot.send_message(cid, f"Слово {target_word} не является пользовательским.")
    next_cards(message)

#-------------------------------------------------------------------------------------------------------

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['adding'] = True
    bot.send_message(cid, "Введите слово, которое хотите добавить:")
    print('data', data)

#--------------------------------------------------------------------------------------------------------

@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 1)
def save_new_word(message):
    cid = message.chat.id
    text = message.text.strip()
    # В случае добавления слова
    if 'new_word' not in user_state.get(cid, {}):
        user_state.setdefault(cid, {})['new_word'] = text
        bot.send_message(cid, "Теперь введите перевод этого слова:")
    else:
        new_word = user_state[cid]['new_word']
        print('new', new_word)
        translation = text
        print(translation)
        add_new_word(cid, new_word, translation)
        # Очистка
        del user_state[cid]
        userStep[cid] = 0

        next_cards(message)

#--------------------------------------------------------------------------------------------------------------

# Обрабатываем любой текст который остался после функций ниже
@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    cid = message.chat.id
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        print('ex', data)
    target_word = data['target_word']

    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons.clear()
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    # удаление слова если оно есть из списка предлагаемых
    other_words = other_cards(cid)
    if target_word in other_words:
        other_words.remove(target_word)
    else:
        del other_words[0]
    other_words_btn = [types.KeyboardButton(word) for word in other_words]
    buttons.extend(other_words_btn)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])
    markup.add(*buttons)

    if message.text == target_word:
        bot.send_message(message.chat.id, "Все правильно")
    else:
        bot.send_message(message.chat.id, 'Ошибка, попробуй еще раз')

bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
