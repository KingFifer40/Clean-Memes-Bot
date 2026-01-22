import sys
sys.stdout.reconfigure(encoding='utf-8') #This ensures that it can run on the raspberry pi

import requests
import uuid
import time
import json
import os

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
TOKEN = "TOKEN"
GROUP_ID = "GROUP_ID"   # Topic group, this is where the bot is interacted with at
MAIN_GROUP_ID = "MAIN_TOPIC"   # This NEEDS to be the main chat, so the script can get the admins for admin commands
YOUR_USER_ID = "USER_ID"

# TEMPORARY admin override (user IDs as strings)
TEMP_ADMIN_OVERRIDE = {
    YOUR_USER_ID  # your user ID, and this can be removed for the bot to stop treating you as an admin.
}

# Default welcome message (admins/owners can change this)
WELCOME_MESSAGE = "Welcome to the group, {name}!" # <----This is not used yet

# Cooldown to prevent spam when multiple people join
last_welcome_time = 0

TRIGGER_FILE = "triggers.json"
MAX_TRIGGERS = 15

GLOBAL_ADMINS = set()

# ---------------------------------------------------------
# Bot Signature
# ---------------------------------------------------------
BOT_SIGNATURE = (
    "\n\n -Clanker"
)

# ---------------------------------------------------------
# URL for API
# ---------------------------------------------------------
BASE_URL = "https://api.groupme.com/v3"

# ---------------------------------------------------------
# GroupMe API helper
# ---------------------------------------------------------
def groupme_api(path, method="GET", data=None):
    url = f"{BASE_URL}/{path}?token={TOKEN}"

    try:
        if method == "GET":
            return requests.get(url, timeout=10).json()
        elif method == "POST":
            return requests.post(url, json=data, timeout=10).json()
    except Exception as e:
        print(f"[ERROR] API request failed: {e}")
        time.sleep(2)
        return None

# ---------------------------------------------------------
# Unified message sender
# ---------------------------------------------------------
def send_message(text, use_signature=True):
    full_text = f"{text}{BOT_SIGNATURE}" if use_signature else text

    message_body = {
        "message": {
            "source_guid": str(uuid.uuid4()),
            "text": full_text
        }
    }

    return groupme_api(f"groups/{GROUP_ID}/messages", method="POST", data=message_body)

# ---------------------------------------------------------
# DAILY LEADERBOARD SYSTEM
# ---------------------------------------------------------
LEADERBOARD_FILE = "daily_leaderboard.json"

def load_daily_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return {
            "tictactoe": {},
            "connectfour": {},
            "checkers": {},
            "last_reset": ""
        }
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "tictactoe": {},
            "connectfour": {},
            "checkers": {},
            "last_reset": ""
        }

def save_daily_leaderboard(lb):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(lb, f)

def add_daily_win(game, user_id, user_name):
    lb = load_daily_leaderboard()

    if game not in lb:
        lb[game] = {}

    if user_id not in lb[game]:
        lb[game][user_id] = {"name": user_name, "wins": 0}

    lb[game][user_id]["wins"] += 1
    save_daily_leaderboard(lb)

def format_top_three(game_data):
    if not game_data:
        return "No winners yet."

    sorted_players = sorted(
        game_data.values(),
        key=lambda x: x["wins"],
        reverse=True
    )

    lines = []
    for i, entry in enumerate(sorted_players[:3]):
        lines.append(f"{i+1}. {entry['name']} — {entry['wins']} wins")

    return "\n".join(lines)

def get_daily_leaderboard_text():
    lb = load_daily_leaderboard()

    return (
        "🏆 **Daily Game Leaders** 🏆\n\n"
        "🎮 **Tic Tac Toe**\n" +
        format_top_three(lb["tictactoe"]) + "\n\n" +
        "🟦 **Connect Four**\n" +
        format_top_three(lb["connectfour"]) + "\n\n" +
        "♟️ **Checkers**\n" +
        format_top_three(lb["checkers"])
    )

def get_daily_winners_text():
    lb = load_daily_leaderboard()

    return (
        "🏁 **Winners of the Day** 🏁\n\n"
        "🎮 **Tic Tac Toe**\n" +
        format_top_three(lb["tictactoe"]) + "\n\n" +
        "🟦 **Connect Four**\n" +
        format_top_three(lb["connectfour"]) + "\n\n" +
        "♟️ **Checkers**\n" +
        format_top_three(lb["checkers"])
    )

def reset_daily_leaderboard_if_needed():
    lb = load_daily_leaderboard()
    today = time.strftime("%Y-%m-%d")

    if lb["last_reset"] != today:

        # Send winners of the previous day
        if lb["last_reset"] != "":
            send_message(get_daily_winners_text())

            # Determine daily champion(s)
            combined = {}

            # Merge all game wins into one total per user
            for game in ["tictactoe", "connectfour", "checkers"]:
                for uid, entry in lb[game].items():
                    combined.setdefault(uid, {"name": entry["name"], "wins": 0})
                    combined[uid]["wins"] += entry["wins"]

            if combined:
                # Find highest score
                max_wins = max(entry["wins"] for entry in combined.values())

                # Award monthly points to all tied winners
                for uid, entry in combined.items():
                    if entry["wins"] == max_wins:
                        add_monthly_point(uid, entry["name"])

        # Reset daily leaderboard
        lb = {
            "tictactoe": {},
            "connectfour": {},
            "checkers": {},
            "last_reset": today
        }
        save_daily_leaderboard(lb)

        # Reset monthly if needed
        monthly_reset_if_needed()

# ---------------------------------------------------------
# MONTHLY LEADERBOARD SYSTEM
# ---------------------------------------------------------
MONTHLY_FILE = "monthly_leaderboard.json"

def load_monthly():
    if not os.path.exists(MONTHLY_FILE):
        return {"leaders": {}, "last_month": ""}
    try:
        with open(MONTHLY_FILE, "r") as f:
            return json.load(f)
    except:
        return {"leaders": {}, "last_month": ""}

def save_monthly(data):
    with open(MONTHLY_FILE, "w") as f:
        json.dump(data, f)

def add_monthly_point(user_id, user_name):
    data = load_monthly()
    if user_id not in data["leaders"]:
        data["leaders"][user_id] = {"name": user_name, "points": 0}
    data["leaders"][user_id]["points"] += 1
    save_monthly(data)

def get_monthly_text():
    data = load_monthly()
    leaders = data["leaders"]

    if not leaders:
        return "No monthly points recorded yet."

    sorted_lb = sorted(leaders.values(), key=lambda x: x["points"], reverse=True)

    lines = ["🌙 **Monthly Leaders** 🌙"]
    for i, entry in enumerate(sorted_lb[:5]):
        lines.append(f"{i+1}. {entry['name']} — {entry['points']} points")

    return "\n".join(lines)

def monthly_reset_if_needed():
    data = load_monthly()
    current_month = time.strftime("%Y-%m")

    if data["last_month"] != current_month:
        # Reset monthly leaderboard
        data = {"leaders": {}, "last_month": current_month}
        save_monthly(data)

# ---------------------------------------------------------
# Helper: Check if a user is already in ANY game
# ---------------------------------------------------------
def user_is_in_any_game(user_id):
    global ttt_active, ttt_player1_id, ttt_player2_id
    global c4_active, c4_player1_id, c4_player2_id

    if 'ttt_active' in globals() and ttt_active:
        if user_id == ttt_player1_id or user_id == ttt_player2_id:
            return True

    if 'c4_active' in globals() and c4_active:
        if user_id == c4_player1_id or user_id == c4_player2_id:
            return True

    return False

# ---------------------------------------------------------
# CUSTOM TRIGGERS (ADMIN-MANAGED)
# ---------------------------------------------------------

def load_triggers():
    if not os.path.exists(TRIGGER_FILE):
        return {"next_id": 1, "triggers": {}}
    try:
        with open(TRIGGER_FILE, "r") as f:
            return json.load(f)
    except:
        return {"next_id": 1, "triggers": {}}

def save_triggers(data):
    with open(TRIGGER_FILE, "w") as f:
        json.dump(data, f)

def handle_addtrigger(msg):
    raw_text = msg.get("text") or ""
    if not raw_text.startswith("!addtrigger"):
        return

    sender_id = str(msg.get("sender_id"))

    admin_ids = get_admin_ids()

    # ---- DEBUG OUTPUT ----
    print("=== ADDTRIGGER DEBUG ===")
    print("Sender ID:", sender_id)
    print("Admin IDs:", admin_ids)
    print("Is admin?", sender_id in admin_ids)
    print("========================")

    if sender_id not in admin_ids:
        send_message("Only admins can add triggers.")
        return

    if '"' not in raw_text:
        send_message('Usage: !addtrigger word "response text"')
        return

    try:
        before, quoted = raw_text.split('"', 1)
        response, _ = quoted.split('"', 1)
        trigger_word = before.split()[1].lower()
    except Exception as e:
        print("Parse error:", e)
        send_message('Usage: !addtrigger word "response text"')
        return

    data = load_triggers()

    if len(data["triggers"]) >= MAX_TRIGGERS:
        send_message("Trigger limit reached (15 max).")
        return

    trigger_id = str(data["next_id"])
    data["next_id"] += 1

    data["triggers"][trigger_id] = {
        "word": trigger_word,
        "response": response
    }

    save_triggers(data)
    send_message(f"Trigger added: `{trigger_word}` (ID {trigger_id})")

def handle_rmtrigger(msg):
    text = msg.get("text") or ""
    sender_id = str(msg.get("sender_id"))

    if not text.startswith("!rmtrigger"):
        return

    if sender_id not in get_admin_ids():
        send_message("Only admins can remove triggers.")
        return

    parts = text.split()
    if len(parts) != 2:
        send_message("Usage: !rmtrigger ID")
        return

    trigger_id = parts[1]
    data = load_triggers()

    if trigger_id not in data["triggers"]:
        send_message("Trigger ID not found.")
        return

    word = data["triggers"][trigger_id]["word"]
    del data["triggers"][trigger_id]
    save_triggers(data)

    send_message(f"Removed trigger `{word}` (ID {trigger_id})")


# ---------------------------------------------------------
# HELP COMMAND
# ---------------------------------------------------------
def get_help_text():
    return (
        "📘-HELP MENU- \n\n"

        "🎮 -Games- \n"
        "#start — Start Tic Tac Toe\n"
        "#join — Join Tic Tac Toe\n"
        "#A1 / #1A — Tic Tac Toe move\n"
        "#addai - adds a second ai player\n"

        "=start — Start Connect Four\n"
        "=join — Join Connect Four\n"
        "=A–G — Drop a piece\n\n"

        "🏆 -Leaderboards- \n"
        "!leaderboard — Today's leaders\n"
        "!monthlyleaders — Monthly leaders\n\n"

        "🧩 -General- \n"
        "!listtriggers — List trigger words\n"
        "!admins - Lists admins\n\n"

        "🔧 -Admin Only- \n"
        "!addtrigger word \"response\"\n"
        "!rmtrigger ID\n"
    )


def handle_help_command(msg):
    text = (msg.get("text") or "").strip().lower()
    if text == "!help":
        send_message(get_help_text())

# ---------------------------------------------------------
# ADMIN / OWNER DETECTION
# ---------------------------------------------------------
def get_admin_ids():
    group_info = groupme_api(f"groups/{MAIN_GROUP_ID}")

    if not group_info or "response" not in group_info:
        print("Admin scan failed: no response from API")
        return set()

    members = group_info["response"].get("members", [])
    admin_ids = set()

    print("Admins detected at startup:")

    for m in members:
        roles = m.get("roles", [])
        if "admin" in roles or "owner" in roles:
            uid = str(m["user_id"])
            name = m.get("name", "Unknown")
            admin_ids.add(uid)
            print(f" - {name} ({uid})")   # <-- ONLY prints admins

    # Add your override
    for uid in TEMP_ADMIN_OVERRIDE:
        print(f" - Override admin ({uid})")
        admin_ids.add(uid)

    return admin_ids

#----------------------ADMIN COMMAND-----------------------
def get_admin_list_text():
    group_info = groupme_api(f"groups/{MAIN_GROUP_ID}")
    if not group_info or "response" not in group_info:
        return "Could not fetch admin list."

    members = group_info["response"].get("members", [])
    admins = []

    for m in members:
        roles = m.get("roles", [])
        if "admin" in roles or "owner" in roles:
            admins.append(f"{m['name']} ({m['user_id']})")

    # Include override admins
    for uid in TEMP_ADMIN_OVERRIDE:
        # Try to match override ID to a name
        name = next((m["name"] for m in members if str(m["user_id"]) == uid), None)
        if name:
            admins.append(f"{name} ({uid})")
        else:
            admins.append(f"Override Admin ({uid})")

    if not admins:
        return "No admins detected."

    return "👑 **Group Admins** 👑\n" + "\n".join(f"- {a}" for a in admins)

# ---------------------------------------------------------
# TIC TAC TOE
# ---------------------------------------------------------

# Game state
ttt_active = False
ttt_player1_id = None
ttt_player2_id = None
ttt_player1_name = None
ttt_player2_name = None
ttt_board = None  # dict like {"A1": "+", ...}
ttt_current_player = None  # "X" or "O"
ttt_last_activity = None  # timestamp
ttt_ai_enabled = False
TTT_EMPTY = "⚫"   # empty space
TTT_P1 = "🔵"      # player X
TTT_P2 = "🔴"      # player O
TTT_AI = "🟢"      # AI

def ttt_init_board():
    return {
        "1A": TTT_EMPTY, "1B": TTT_EMPTY, "1C": TTT_EMPTY,
        "2A": TTT_EMPTY, "2B": TTT_EMPTY, "2C": TTT_EMPTY,
        "3A": TTT_EMPTY, "3B": TTT_EMPTY, "3C": TTT_EMPTY
    }


def ttt_board_to_text():
    row1 = f"1  {ttt_board['1A']} {ttt_board['1B']} {ttt_board['1C']}"
    row2 = f"2  {ttt_board['2A']} {ttt_board['2B']} {ttt_board['2C']}"
    row3 = f"3  {ttt_board['3A']} {ttt_board['3B']} {ttt_board['3C']}"
    header = "   A B C"
    return f"{header}\n{row1}\n{row2}\n{row3}"


def ttt_reset(reason=None):
    global ttt_active, ttt_player1_id, ttt_player2_id
    global ttt_player1_name, ttt_player2_name, ttt_board
    global ttt_current_player, ttt_last_activity

    ttt_active = False
    ttt_player1_id = None
    ttt_player2_id = None
    ttt_player1_name = None
    ttt_player2_name = None
    ttt_board = None
    ttt_current_player = None
    ttt_last_activity = None

    if reason:
        send_message(reason)


def ttt_check_inactivity():
    if not ttt_active or ttt_last_activity is None:
        return
    if time.time() - ttt_last_activity > 300:
        ttt_reset("The Tic Tac Toe game has been reset due to 5 minutes of inactivity.")


def ttt_check_winner():
    b = ttt_board

    lines = [
        ("1A", "1B", "1C"),
        ("2A", "2B", "2C"),
        ("3A", "3B", "3C"),

        ("1A", "2A", "3A"),
        ("1B", "2B", "3B"),
        ("1C", "2C", "3C"),

        ("1A", "2B", "3C"),
        ("1C", "2B", "3A"),
    ]

    for a, c, d in lines:
        if b[a] != TTT_EMPTY and b[a] == b[c] == b[d]:
            return b[a]

    if all(v != TTT_EMPTY for v in b.values()):
        return "draw"

    return None


def ttt_handle_start(msg):
    global ttt_active, ttt_player1_id, ttt_player1_name
    global ttt_board, ttt_current_player, ttt_last_activity, ttt_ai_enabled

    sender_id = msg.get("sender_id")
    sender_name = msg.get("name") or "Someone"

    if ttt_active:
        send_message(
            f"A Tic Tac Toe game is already in progress between "
            f"{ttt_player1_name} and {ttt_player2_name or 'waiting for Player 2'}."
        )
        return

    ttt_active = True
    ttt_ai_enabled = False  # reset AI
    ttt_player1_id = sender_id
    ttt_player1_name = sender_name
    ttt_board = ttt_init_board()
    ttt_current_player = "X"
    ttt_last_activity = time.time()

    send_message(
        f"{ttt_player1_name} has started a Tic Tac Toe game! Player one, start. "
        f"Say #join to join, or #addai to play against an AI."
    )

def ttt_handle_join(msg):
    global ttt_player2_id, ttt_player2_name, ttt_last_activity

    if not ttt_active:
        return

    sender_id = msg.get("sender_id")
    sender_name = msg.get("name") or "Someone"

    if ttt_player2_id is not None:
        send_message(
            f"A Tic Tac Toe game is already going between {ttt_player1_name} and {ttt_player2_name}."
        )
        return

    if sender_id == ttt_player1_id:
        send_message("You cannot join your own game — you are already Player 1. Try adding an ai player with #addai.")
        return

    ttt_player2_id = sender_id
    ttt_player2_name = sender_name
    ttt_last_activity = time.time()

    send_message(
        f"{ttt_player2_name} has joined! {ttt_player1_name} is {TTT_P1} and {ttt_player2_name} is {TTT_P2}. "
        f"{ttt_player1_name} starts."
    )
    send_message("Current board:\n" + ttt_board_to_text())
    
def ttt_handle_add_ai(msg):
    global ttt_ai_enabled, ttt_player2_id, ttt_player2_name

    if not ttt_active:
        send_message("Start a game first with #start.", use_signature=False)
        return

    if ttt_player2_id is not None:
        send_message("A second player has already joined.", use_signature=False)
        return

    ttt_ai_enabled = True
    ttt_player2_id = "AI"
    ttt_player2_name = "AI"

    send_message(f"AI has joined as {TTT_AI}. Good luck!", use_signature=False)

    # If AI goes first
    if ttt_current_player == "O":
        ttt_ai_make_move()

def ttt_ai_make_move():
    global ttt_board, ttt_current_player, ttt_last_activity

    best_score = -999
    best_move = None

    for move, value in ttt_board.items():
        if value == TTT_EMPTY:
            ttt_board[move] = TTT_AI
            score = ttt_minimax(ttt_board, False)
            ttt_board[move] = TTT_EMPTY
            if score > best_score:
                best_score = score
                best_move = move

    # Make the move
    ttt_board[best_move] = TTT_AI
    ttt_last_activity = time.time()

    send_message(
        f"AI chose {best_move}.\nCurrent board:\n" + ttt_board_to_text(),
        use_signature=False
    )

    result = ttt_check_winner()

    if result == TTT_AI:
        send_message("AI has won the Tic Tac Toe game!", use_signature=False)
        ttt_reset()
        return

    if result == "draw":
        send_message("The Tic Tac Toe game is a draw!", use_signature=False)
        ttt_reset()
        return

    ttt_current_player = "X"
    send_message(f"It is now {ttt_player1_name}'s turn (X).")

def ttt_minimax(board, is_maximizing):
    winner = ttt_check_winner()

    if winner == TTT_AI:
        return 1
    if winner == TTT_P1:
        return -1
    if winner == "draw":
        return 0

    if is_maximizing:
        best_score = -999
        for move, value in board.items():
            if value == TTT_EMPTY:
                board[move] = TTT_AI
                score = ttt_minimax(board, False)
                board[move] = TTT_EMPTY
                best_score = max(score, best_score)
        return best_score

    else:
        best_score = 999
        for move, value in board.items():
            if value == TTT_EMPTY:
                board[move] = TTT_P1
                score = ttt_minimax(board, True)
                board[move] = TTT_EMPTY
                best_score = min(score, best_score)
        return best_score

def ttt_normalize_move(raw):
    """
    Accepts #A1, #1A, #b2, #2b, etc.
    Returns normalized form like "1A" or None if invalid.
    """
    if not raw.startswith("#"):
        return None

    coord = raw[1:].upper()

    if len(coord) != 2:
        return None

    c1, c2 = coord[0], coord[1]

    letter = c1 if c1 in "ABC" else c2 if c2 in "ABC" else None
    number = c1 if c1 in "123" else c2 if c2 in "123" else None

    if not letter or not number:
        return None

    return number + letter  # internal format


def ttt_handle_move(msg):
    global ttt_current_player, ttt_last_activity

    if not ttt_active or ttt_player2_id is None:
        return

    raw = (msg.get("text") or "").strip().upper()
    move = ttt_normalize_move(raw)

    if move is None:
        return

    valid_moves = {
        "1A", "1B", "1C",
        "2A", "2B", "2C",
        "3A", "3B", "3C"
    }

    if move not in valid_moves:
        return

    sender_id = msg.get("sender_id")
    sender_name = msg.get("name") or "Someone"

    # Enforce turn order
    if ttt_current_player == "X" and sender_id != ttt_player1_id:
        send_message(f"It is {ttt_player1_name}'s turn {TTT_P1}.")
        return

    if ttt_current_player == "O" and not ttt_ai_enabled and sender_id != ttt_player2_id:
        send_message(f"It is {ttt_player2_name}'s turn {TTT_P2}.")
        return

    if ttt_board[move] != TTT_EMPTY:
        send_message("That spot is already taken.")
        return

    # Human move
    ttt_board[move] = TTT_P1 if ttt_current_player == "X" else TTT_P2
    ttt_last_activity = time.time()

    send_message(f"{sender_name} played {move}.\nCurrent board:\n" + ttt_board_to_text())

    result = ttt_check_winner()

    if result == TTT_P1:
        add_daily_win("tictactoe", ttt_player1_id, ttt_player1_name)
        send_message(f"{ttt_player1_name} (🔵) has won the Tic Tac Toe game!")
        ttt_reset()
        return

    if result == TTT_P2 or result == TTT_AI:
        add_daily_win("tictactoe", ttt_player2_id, ttt_player2_name)
        winner_name = ttt_player2_name if not ttt_ai_enabled else "AI"
        send_message(f"{winner_name} has won the Tic Tac Toe game!")
        ttt_reset()
        return

    if result == "draw":
        send_message("The Tic Tac Toe game is a draw!")
        ttt_reset()
        return

    # Switch turn
    ttt_current_player = "O" if ttt_current_player == "X" else "X"

    # AI turn
    if ttt_ai_enabled and ttt_current_player == "O":
        ttt_ai_make_move()
        return

    # Human turn
    next_name = ttt_player1_name if ttt_current_player == "X" else ttt_player2_name
    send_message(f"It is now {next_name}'s turn ({ttt_current_player}).")


def handle_tictactoe(msg):
    text = (msg.get("text") or "").lower().strip()

    ttt_check_inactivity()

    if text == "#start":
        ttt_handle_start(msg)
    elif text == "#join":
        ttt_handle_join(msg)
    elif text == "#addai":
        ttt_handle_add_ai(msg)
    else:
        ttt_handle_move(msg)

# ---------------------------------------------------------
# CONNECT FOUR
# ---------------------------------------------------------

# Game state
c4_active = False
c4_player1_id = None
c4_player2_id = None
c4_player1_name = None
c4_player2_name = None
c4_board = None  # list of 7 columns, each column is a list of 6 cells
c4_current_player = None  # "X" or "O"
c4_last_activity = None  # timestamp

def c4_init_board():
    # 7 columns, each with 6 rows
    return [["+" for _ in range(6)] for _ in range(7)]

def c4_board_to_text():
    # Box-drawing style
    header = "    A   B   C   D   E   F   G"
    rows = []

    for row in range(5, -1, -1):  # 6 → 1
        line = f"{row+1} "
        for col in range(7):
            line += f"| {c4_board[col][row]} "
        line += "|"
        rows.append(line)

    return header + "\n" + "\n".join(rows)

def c4_reset(reason=None):
    global c4_active, c4_player1_id, c4_player2_id
    global c4_player1_name, c4_player2_name
    global c4_board, c4_current_player, c4_last_activity

    c4_active = False
    c4_player1_id = None
    c4_player2_id = None
    c4_player1_name = None
    c4_player2_name = None
    c4_board = None
    c4_current_player = None
    c4_last_activity = None

    if reason:
        send_message(reason)

def c4_check_inactivity():
    if not c4_active or c4_last_activity is None:
        return
    if time.time() - c4_last_activity > 300:
        c4_reset("The Connect Four game has been reset due to 5 minutes of inactivity.")

def c4_handle_start(msg):
    global c4_active, c4_player1_id, c4_player1_name
    global c4_board, c4_current_player, c4_last_activity

    sender_id = msg.get("sender_id")
    sender_name = msg.get("name") or "Someone"

    if c4_active:
        send_message(
            f"A Connect Four game is already in progress between "
            f"{c4_player1_name} and {c4_player2_name or 'waiting for Player 2'}."
        )
        return

    # Prevent user from playing two games at once
    if user_is_in_any_game(sender_id):
        send_message("You are already playing a game. Finish it before starting another.")
        return

    c4_active = True
    c4_player1_id = sender_id
    c4_player1_name = sender_name
    c4_board = c4_init_board()
    c4_current_player = "X"
    c4_last_activity = time.time()

    send_message(
        f"{c4_player1_name} has started a Connect Four game! "
        f"Say =join to join as Player 2."
    )

def c4_handle_join(msg):
    global c4_player2_id, c4_player2_name, c4_last_activity

    if not c4_active:
        return

    sender_id = msg.get("sender_id")
    sender_name = msg.get("name") or "Someone"

    if c4_player2_id is not None:
        send_message(
            f"A Connect Four game is already going between {c4_player1_name} and {c4_player2_name}."
        )
        return

    if sender_id == c4_player1_id:
        send_message("You cannot join your own game — you are already Player 1.")
        return

    # Prevent user from playing two games at once
    if user_is_in_any_game(sender_id):
        send_message("You are already playing a game. Finish it before joining another.")
        return

    c4_player2_id = sender_id
    c4_player2_name = sender_name
    c4_last_activity = time.time()

    send_message(
        f"{c4_player2_name} has joined! {c4_player1_name} is X and {c4_player2_name} is O. "
        f"{c4_player1_name} starts."
    )
    send_message("Current board:\n" + c4_board_to_text())

def c4_drop_piece(col_index, piece):
    column = c4_board[col_index]
    for i in range(6):
        if column[i] == "+":
            column[i] = piece
            return i
    return None  # column full

def c4_check_winner():
    b = c4_board

    # Horizontal
    for row in range(6):
        for col in range(4):
            line = [b[col+i][row] for i in range(4)]
            if line[0] != "+" and all(x == line[0] for x in line):
                return line[0]

    # Vertical
    for col in range(7):
        for row in range(3):
            line = [b[col][row+i] for i in range(4)]
            if line[0] != "+" and all(x == line[0] for x in line):
                return line[0]

    # Diagonal /
    for col in range(4):
        for row in range(3):
            line = [b[col+i][row+i] for i in range(4)]
            if line[0] != "+" and all(x == line[0] for x in line):
                return line[0]

    # Diagonal \
    for col in range(4):
        for row in range(3, 6):
            line = [b[col+i][row-i] for i in range(4)]
            if line[0] != "+" and all(x == line[0] for x in line):
                return line[0]

    # Draw
    if all(b[col][5] != "+" for col in range(7)):
        return "draw"

    return None

def c4_handle_move(msg):
    global c4_current_player, c4_last_activity

    if not c4_active or c4_player2_id is None:
        return

    text = (msg.get("text") or "").strip().upper()
    if not text.startswith("="):
        return

    move = text[1:]
    if move not in "ABCDEFG":
        return

    col_index = "ABCDEFG".index(move)

    sender_id = msg.get("sender_id")
    sender_name = msg.get("name") or "Someone"

    # Turn enforcement
    if c4_current_player == "X" and sender_id != c4_player1_id:
        send_message(f"It is {c4_player1_name}'s turn (X).")
        return
    if c4_current_player == "O" and sender_id != c4_player2_id:
        send_message(f"It is {c4_player2_name}'s turn (O).")
        return

    row = c4_drop_piece(col_index, c4_current_player)
    if row is None:
        send_message("That column is full.")
        return

    c4_last_activity = time.time()

    send_message(
        f"{sender_name} played in column {move}.\nCurrent board:\n" + c4_board_to_text()
    )

    result = c4_check_winner()

    if result == "X":
        add_daily_win("connectfour", c4_player1_id, c4_player1_name)
        send_message(f"{c4_player1_name} (X) has won the Connect Four game!")
        c4_reset()
        return

    elif result == "O":
        add_daily_win("connectfour", c4_player2_id, c4_player2_name)
        send_message(f"{c4_player2_name} (O) has won the Connect Four game!")
        c4_reset()
        return

    elif result == "draw":
        send_message("The Connect Four game is a draw!")
        c4_reset()
        return

    c4_current_player = "O" if c4_current_player == "X" else "X"
    next_name = c4_player1_name if c4_current_player == "X" else c4_player2_name
    send_message(f"It is now {next_name}'s turn ({c4_current_player}).")

def handle_connect_four(msg):
    text = (msg.get("text") or "").lower().strip()

    c4_check_inactivity()

    if text == "=start":
        c4_handle_start(msg)
    elif text == "=join":
        c4_handle_join(msg)
    else:
        c4_handle_move(msg)

# ---------------------------------------------------------
# Function: check if a message triggers the bot (counter)
# ---------------------------------------------------------
def handle_triggers(msg):
    text = (msg.get("text") or "").lower()
    if not text:
        return

    # Ignore bot-generated messages
    if text.endswith(BOT_SIGNATURE.strip().lower()):
        return

    data = load_triggers()

    for t in data["triggers"].values():
        if t["word"] in text:
            send_message(t["response"], use_signature=True)
            return

def handle_listtriggers(msg):
    text = msg.get("text") or ""
    if text != "!listtriggers":
        return

    data = load_triggers()
    triggers = data.get("triggers", {})

    if not triggers:
        send_message("No triggers are currently set.")
        return

    lines = ["Triggers:"]
    for tid, info in triggers.items():
        lines.append(f"{tid}: {info['word']}")

    send_message("\n".join(lines))


# ---------------------------------------------------------
# Polling loop: watch for mentions, triggers, join events, and games
# ---------------------------------------------------------
def watch_for_mentions():
    print("Watching for mentions, trigger words, Tic Tac Toe, Connect Four, and join events...")

    data = groupme_api(f"groups/{GROUP_ID}/messages")
    if data is None:
        print("[ERROR] Could not fetch initial messages.")
        time.sleep(2)
        return

    last_seen_id = data["response"]["messages"][0]["id"]

    while True:
        time.sleep(2)

        # 🔥 DAILY RESET (also awards monthly points)
        reset_daily_leaderboard_if_needed()

        data = groupme_api(f"groups/{GROUP_ID}/messages")
        if data is None:
            print("[WARN] No data returned, retrying...")
            time.sleep(2)
            continue

        messages = data["response"]["messages"]
        new_last_seen = last_seen_id

        for msg in messages:
            msg_id = msg["id"]

            # Stop when we reach messages we've already processed
            if msg_id == last_seen_id:
                break

            text = (msg.get("text") or "").lower().strip()

            # -------------------------------
            # GAME HANDLERS
            # -------------------------------
            handle_tictactoe(msg)
            handle_connect_four(msg)

            # -------------------------------
            # HELP COMMAND
            # -------------------------------
            handle_help_command(msg)
            
            # -------------------------------
            # TRIGGERS
            # -------------------------------
            handle_triggers(msg)
            handle_addtrigger(msg)
            handle_listtriggers(msg)
            handle_rmtrigger(msg)

            # -------------------------------
            # MONTHLY LEADERBOARD COMMAND
            # -------------------------------
            if text == "!monthlyleaders":
                send_message(get_monthly_text())

            # -------------------------------
            # ADMIN LIST COMMAND
            # -------------------------------
            if text == "!admins":
                send_message(get_admin_list_text(), use_signature=False)

            # -------------------------------
            # DAILY LEADERBOARD COMMAND
            # -------------------------------
            if text == "!leaderboard":
                send_message(get_daily_leaderboard_text())

            # Track newest message
            if new_last_seen == last_seen_id:
                new_last_seen = msg_id

        last_seen_id = new_last_seen
        
# ---------------------------------------------------------
# Start the bot
# ---------------------------------------------------------
# Force an admin scan at startup
print("Scanning for admins at startup...")
admins = get_admin_ids()
print("Admins detected:", admins)
print("TEMP_ADMIN_OVERRIDE:", TEMP_ADMIN_OVERRIDE)

# Start the bot
watch_for_mentions()