import sqlite3, json
database = sqlite3.connect("leaderboard.db", check_same_thread=False)
cursor = database.cursor()

def add_point(chatID: int, userID: int, username: str) -> None:
    userID = str(userID)
    cursor.execute("SELECT leaderboard FROM leaderboard WHERE chatID=?", (chatID,))
    response = cursor.fetchone()
    if not response: create_leaderboard(chatID)
    cursor.execute("SELECT leaderboard FROM leaderboard WHERE chatID=?", (chatID,))
    response = cursor.fetchone()
    lb = json.loads(response[0])
    if userID in list(lb.keys()): lb[userID]["point"]+=1
    else:
        lb[userID] = {"point": 1, "username": username}
    cursor.execute("UPDATE leaderboard SET leaderboard=? WHERE chatID=?", (json.dumps(lb), chatID))
    database.commit()

def create_leaderboard(chatID: int) -> None:
    cursor.execute("INSERT INTO leaderboard VALUES (?, ?)", (chatID, "{}"))
    database.commit()

def get_leaderboard(chatID: int) -> dict:
    cursor.execute("SELECT leaderboard FROM leaderboard WHERE chatID=?", (chatID,))
    response = cursor.fetchone()
    if not response: return {}
    return json.loads(response[0])