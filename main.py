import telebot
from telebot.util import quick_markup
import json, sqlite3, random

def get_random_word():
    conn = sqlite3.connect("words.db")
    cur = conn.cursor()
    cur.execute("SELECT word FROM words ORDER BY RANDOM() LIMIT 1")
    word = cur.fetchone()[0]
    conn.close()
    return word

def check_admin(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    chat_member = bot.get_chat_member(chat_id, user_id)
    print(chat_member.status)
    return chat_member.status in ['administrator', 'creator', 'owner']

database = sqlite3.connect("bot.db", check_same_thread=False)
cursor = database.cursor()
API_TOKEN = ''

bot = telebot.TeleBot(API_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type=="group":
        markup = quick_markup({
            "Crocodile": {"callback_data": "crocodile"}
        })
        bot.send_message(message.chat.id, "Oynamaq istediyiniz oyunu secin", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Bunu isletmek ucun qrupda olmalisan")


@bot.message_handler(content_types=['text'])
def yoxla(message):
    cursor.execute("SELECT * FROM cro WHERE chatID = ?", (message.chat.id,))
    res = cursor.fetchone()
    if message.text.lower()==res[1].lower() and message.from_user.id != res[2]:
        bot.send_message(message.chat.id, f"{message.from_user.first_name} {res[1]} sozunu tapdi!")
        cursor.execute("UPDATE cro SET currentPlayer=?, currentWord=?", (message.from_user.id, get_random_word()))
        database.commit()
        markup = quick_markup({
            "Sozu gor": {"callback_data": "show_word"}
        })
        bot.send_message(message.chat.id, f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a> yeni sozu izah edir!', reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: True)
def reply(call):
    if call.data == "crocodile":
        cursor.execute(f"SELECT chatID FROM cro WHERE chatID=={call.message.chat.id}")
        if not cursor.fetchall(): 
            print("Ok")
            cursor.execute(f"INSERT INTO cro VALUES ({call.message.chat.id}, '', 0, '[]', '[]')")
        else: 
            print("Yok")
            cursor.execute(f"""UPDATE cro 
                             SET currentWord = '',
                             currentPlayer = 0,
                             players = '[]',
                             playerNames = '[]'
                             WHERE chatID={call.message.chat.id}""")
        database.commit()
        markup = quick_markup({
            "Qosul": {"callback_data": "cro_join"},
            "Cix": {"callback_data": "cro_leave"},
            "Baslat": {"callback_data": "cro_start"}
        })
        bot.edit_message_text("""Oyun bir azdan baslayacaq.\nQosulanlar:""", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data == "cro_join":
        cursor.execute(f"SELECT players, playerNames FROM cro WHERE chatID={call.message.chat.id}")
        res = cursor.fetchone()
        players = json.loads(res[0])
        playerNames = json.loads(res[1])
        if not call.from_user.id in players:
            players.append(call.from_user.id)
            playerNames.append(call.from_user.first_name)
            cursor.execute(
            "UPDATE cro SET players = ?, playerNames = ? WHERE chatID = ?",
            (json.dumps(players), json.dumps(playerNames), call.message.chat.id)
            )
            database.commit()
            markup = quick_markup({
            "Qosul": {"callback_data": "cro_join"},
            "Cix": {"callback_data": "cro_leave"},
            "Baslat": {"callback_data": "cro_start"}
            })
            bot.edit_message_text("Oyun bir azdan baslayacaq.\nQosulanlar: "+", ".join([f'<a href="tg://user?id={players[i]}">{playerNames[i]}</a>' for i in range(len(players))]), parse_mode="HTML", reply_markup=markup, message_id=call.message.message_id, chat_id=call.message.chat.id)
    elif call.data == "cro_leave":
        cursor.execute(f"SELECT players, playerNames FROM cro WHERE chatID={call.message.chat.id}")
        res = cursor.fetchone()
        players = json.loads(res[0])
        playerNames = json.loads(res[1])
        if call.from_user.id in players:
            ndx = players.index(call.from_user.id)
            del players[ndx]
            del playerNames[ndx]
            cursor.execute(
            "UPDATE cro SET players = ?, playerNames = ? WHERE chatID = ?",
            (json.dumps(players), json.dumps(playerNames), call.message.chat.id)
            )
            database.commit()
            markup = quick_markup({
            "Qosul": {"callback_data": "cro_join"},
            "Cix": {"callback_data": "cro_leave"},
            "Baslat": {"callback_data": "cro_start"}
            })
            bot.edit_message_text(f"Oyun bir azdan baslayacaq.\nQosulanlar: "+", ".join([f'<a href="tg://user?id={players[i]}">{playerNames[i]}</a>' for i in range(len(players))]), parse_mode="HTML", reply_markup=markup, message_id=call.message.message_id, chat_id=call.message.chat.id)
    elif call.data == "cro_start":
        if check_admin(call):
            cursor.execute("SELECT players, playerNames FROM cro WHERE chatID=?", (call.message.chat.id,))
            players, playerNames = map(json.loads, cursor.fetchone())
            if len(players)>=2:
                rndPlayer = random.randrange(0, len(players))
                cursor.execute("UPDATE cro SET currentPlayer=?, currentWord=?", (players[rndPlayer], get_random_word()))
                database.commit()
                markup = quick_markup({
                    "Sozu gor": {"callback_data": "show_word"}
                })
                bot.edit_message_text(f"Oyun basladi, {playerNames[rndPlayer]} sozu izah edir.", call.message.chat.id, call.message.message_id, reply_markup=markup)
            else: bot.answer_callback_query(call.id, "Oyuna baslamaq ucun en azi 2 nefer olmalidir.", show_alert=True)
        else: bot.answer_callback_query(call.id, "Admin deyilsen qaqas", show_alert=True)
    elif call.data == "show_word":
        cursor.execute("SELECT currentWord, currentPlayer FROM cro WHERE chatID=?", (call.message.chat.id,))
        currentWord, currentPlayer = cursor.fetchone()
        if currentPlayer==call.from_user.id:
            bot.answer_callback_query(call.id, currentWord, show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Sizin siraniz deyil", show_alert=True)


bot.infinity_polling()