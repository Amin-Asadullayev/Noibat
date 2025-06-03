import telebot
from telebot.util import quick_markup
import json, sqlite3, random, os, leaderboard
from dotenv import load_dotenv
load_dotenv()

def number_to_emoji(num: int) -> str:
    if num in [1,2,3]: return ["🥇", "🥈", "🥉"][num-1]
    num_emoji = {0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣"}
    result = ""
    while num>0:
        result = num_emoji[num%10] + result
        num//=10
    return result

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
    return chat_member.status in ['administrator', 'creator', 'owner']

database = sqlite3.connect("bot.db", check_same_thread=False)
cursor = database.cursor()

yeni_soz = {
            "Sözə bax 📝": {"callback_data": "show_word"},
            "Fikrimi dəyişdim ❌": {"callback_data": "change_player"},
            "Sözü dəyiş 🔄": {"callback_data": "change_word"}
           }
user_options = {
            "Qoşul": {"callback_data": "cro_join"},
            "Tərk et": {"callback_data": "cro_leave"},
            "Başlat": {"callback_data": "cro_start"}
            }
bot = telebot.TeleBot(os.environ.get("BOT_TOKEN"))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type in ["group", "supergroup"]:
        markup = quick_markup({
            "Crocodile": {"callback_data": "crocodile"}
        })
        bot.send_message(message.chat.id, "Oynamaq istədiyiniz oyunu seçin:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Botdan istifadə etmək üçün qrupda olmalısınız")

@bot.message_handler(commands=["leaderboard"])
def send_lb(message):
    lb = leaderboard.get_leaderboard(message.chat.id)
    if lb=={}:
        bot.send_message(message.chat.id, "Sıralama mövcud deyil.")
    else: 
        n = 0
        lb_sent = "\n".join(f"{number_to_emoji((n:=n+1))} <b>{i[1]['username']}</b> - {i[1]['point']}" for i in sorted(lb.items(), key=lambda item: item[1]['point'], reverse=True)[:10])
        lb_sent = "<b>🏆 Sıralama:</b>\n\n"+lb_sent
        if (len(lb.keys())>10):
            bot.send_message(message.chat.id, lb_sent, parse_mode="HTML", reply_markup=quick_markup({
                "Növbəti səhifə ➡️": {"callback_data": "pageswap_1"}
            }))
        else: bot.send_message(message.chat.id, lb_sent, parse_mode="HTML")

@bot.message_handler(content_types=['text'])
def yoxla(message):
    print("ok")
    cursor.execute("SELECT * FROM cro WHERE chatID = ?", (message.chat.id,))
    res = cursor.fetchone()
    if message.text.lower()==res[1].lower() and message.from_user.id != res[2]:
        bot.send_message(message.chat.id, f"🎉 <b>{message.from_user.first_name}</b> sözü tapdı! <b>{res[1]}</b>", parse_mode="HTML")
        cursor.execute("UPDATE cro SET currentPlayer=?, currentWord=?", (message.from_user.id, get_random_word()))
        leaderboard.add_point(message.chat.id, message.from_user.id, message.from_user.first_name)
        database.commit()
        markup = quick_markup(yeni_soz)
        bot.send_message(message.chat.id, f'<a href="tg://user?id={message.from_user.id}">🎤 {message.from_user.first_name}</a> yeni aparıcıdır! İzah edir:', reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: True)
def reply(call):
    if call.data == "crocodile":
        cursor.execute(f"SELECT chatID FROM cro WHERE chatID=={call.message.chat.id}")
        if not cursor.fetchall(): 
            cursor.execute(f"INSERT INTO cro VALUES ({call.message.chat.id}, '', 0, '[]', '[]')")
        else: 
            cursor.execute(f"""UPDATE cro 
                             SET currentWord = '',
                             currentPlayer = 0,
                             players = '[]',
                             playerNames = '[]'
                             WHERE chatID={call.message.chat.id}""")
        database.commit()
        markup = quick_markup(user_options)
        bot.edit_message_text("""Oyun bir az sonra başlayacaq.\nQoşulanlar:""", call.message.chat.id, call.message.message_id, reply_markup=markup)
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
            markup = quick_markup(user_options)
            bot.edit_message_text("Oyun bir az sonra başlayacaq.\nQoşulanlar: "+", ".join([f'<a href="tg://user?id={players[i]}">{playerNames[i]}</a>' for i in range(len(players))]), parse_mode="HTML", reply_markup=markup, message_id=call.message.message_id, chat_id=call.message.chat.id)
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
            markup = quick_markup(user_options)
            bot.edit_message_text(f"Oyun bir az sonra başlayacaq.\nQoşulanlar: "+", ".join([f'<a href="tg://user?id={players[i]}">{playerNames[i]}</a>' for i in range(len(players))]), parse_mode="HTML", reply_markup=markup, message_id=call.message.message_id, chat_id=call.message.chat.id)
    elif call.data == "cro_start":
        if check_admin(call):
            cursor.execute("SELECT players, playerNames FROM cro WHERE chatID=?", (call.message.chat.id,))
            players, playerNames = map(json.loads, cursor.fetchone())
            if len(players)>=2:
                rndPlayer = random.randrange(0, len(players))
                cursor.execute("UPDATE cro SET currentPlayer=?, currentWord=?", (players[rndPlayer], get_random_word()))
                database.commit()
                markup = quick_markup(yeni_soz)
                bot.edit_message_text(f"Oyun başladı!", call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, f'<a href="tg://user?id={players[rndPlayer]}">🎤 {playerNames[rndPlayer]}</a> yeni aparıcıdır! İzah edir:', reply_markup=markup, parse_mode="HTML")
            else: bot.answer_callback_query(call.id, "❌ Oyuna başlamaq üçün ən azı 2 nəfər olmalıdır!", show_alert=True)
        else: bot.answer_callback_query(call.id, "❌ Oyunu başlatmaq üçün admin olmalısınız!", show_alert=True)
    elif call.data == "change_player":
        print("YOK")
        cursor.execute("SELECT players, playerNames, currentPlayer FROM cro WHERE chatID=?", (call.message.chat.id,))
        players, playerNames, currentPlayer = cursor.fetchone()
        players, playerNames = json.loads(players), json.loads(playerNames)
        if call.from_user.id==currentPlayer:
            ndx = players.index(currentPlayer)
            del players[ndx]
            del playerNames[ndx]
            new_player= random.randrange(0, len(players))
            cursor.execute("UPDATE cro SET currentPlayer=?, currentWord=?", (players[new_player], get_random_word()))
            database.commit()
            markup = quick_markup(yeni_soz)
            bot.send_message(call.message.chat.id, f'<a href="tg://user?id={players[new_player]}">🎤 {playerNames[new_player]}</a> yeni aparıcıdır! İzah edir:', reply_markup=markup, parse_mode="HTML")
        else:
            bot.answer_callback_query(call.id, "❌ Yalnız hazırkı aparıcı imtina edə bilər!", show_alert=True)
    elif call.data == "show_word":
        cursor.execute("SELECT currentWord, currentPlayer FROM cro WHERE chatID=?", (call.message.chat.id,))
        currentWord, currentPlayer = cursor.fetchone()
        if currentPlayer==call.from_user.id:
            bot.answer_callback_query(call.id, currentWord, show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Siz aparıcı deyilsiniz və sözə baxa bilməzsiniz/dəyişə bilməzsiniz", show_alert=True)
    elif call.data == "change_word":
        cursor.execute("SELECT currentPlayer FROM cro WHERE chatID=?", (call.message.chat.id,))
        currentPlayer = cursor.fetchone()[0]
        if currentPlayer==call.from_user.id:
            new_word = get_random_word()
            cursor.execute("UPDATE cro SET currentWord=? WHERE chatID=?",(new_word, call.message.chat.id))
            database.commit()
            bot.answer_callback_query(call.id, new_word, show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Siz aparıcı deyilsiniz və sözə baxa bilməzsiniz/dəyişə bilməzsiniz", show_alert=True)
    elif call.data.startswith("pageswap_"):
        page = int(call.data[9:])
        bot.send_message(call.message.chat.id, page)
        lb = leaderboard.get_leaderboard(call.message.chat.id)
        n = (page*10)
        lb_sent = "\n".join( f"{number_to_emoji((n:=n+1))} <b>{i[1]['username']}</b> - {i[1]['point']}" for i in sorted(lb.items(), key=lambda item: item[1]['point'], reverse=True)[page*10:(page+1)*10])
        lb_sent = "<b>🏆 Sıralama:</b>\n\n"+lb_sent
        if (len(lb.keys())>10*(page)):
            bot.send_message(call.message.chat.id, lb_sent, parse_mode="HTML", reply_markup=quick_markup({
                "⬅️ Əvvəlki səhifə": {"callback_data": f"pageswap_{page-1}"},
                "Növbəti səhifə ➡️": {"callback_data": f"pageswap_{page+1}"}
            } if page>0 else {
                "Növbəti səhifə ➡️": {"callback_data": f"pageswap_{page+1}"}
            }))
        else:
            bot.send_message(call.message.chat.id, lb_sent, parse_mode="HTML", reply_markup=quick_markup({
                "⬅️ Əvvəlki səhifə": {"callback_data": f"pageswap_{page-1}"}
                }) if page>0 else None)

bot.infinity_polling()