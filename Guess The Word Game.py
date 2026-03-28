import random
import sqlite3
import tkinter as tk
import hashlib
from tkinter import messagebox, ttk

#Database
DB_NAME = "pythondatabase.db" 
def get_connection():
    return sqlite3.connect(DB_NAME)


def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            password_hash TEXT DEFAULT '',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            result TEXT,
            date_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(player_id) REFERENCES players(id)
        )
    """)

    # Safe migration for older DBs created before authentication support.
    cursor.execute("PRAGMA table_info(players)")
    columns = [row[1] for row in cursor.fetchall()]
    if "password_hash" not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN password_hash TEXT DEFAULT ''")

    conn.commit()
    conn.close()


def hash_password(username, password):
    normalized = username.strip().lower().encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), normalized, 120000)
    return derived.hex()


def register_player(player_name, password):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_name = player_name.strip().title()
    cursor.execute("SELECT id FROM players WHERE name = ?", (normalized_name,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return None

    pwd_hash = hash_password(normalized_name, password)
    cursor.execute(
        "INSERT INTO players (name, password_hash) VALUES (?, ?)",
        (normalized_name, pwd_hash),
    )
    conn.commit()
    player_id = cursor.lastrowid
    conn.close()
    return player_id


def authenticate_player(player_name, password):
    conn = get_connection()
    cursor = conn.cursor()

    normalized_name = player_name.strip().title()
    cursor.execute(
        "SELECT id, password_hash FROM players WHERE name = ?",
        (normalized_name,),
    )
    player = cursor.fetchone()

    conn.close()

    if not player:
        return None

    player_id, password_hash = player
    if not password_hash:
        return None

    if hash_password(normalized_name, password) == password_hash:
        return player_id
    return None


def update_stats(player_id, result):
    conn = get_connection()
    cursor = conn.cursor()

    if result == "win":
        cursor.execute("UPDATE players SET wins = wins + 1, games_played = games_played + 1 WHERE id = ?", (player_id,))
    else:
        cursor.execute("UPDATE players SET losses = losses + 1, games_played = games_played + 1 WHERE id = ?", (player_id,))

    cursor.execute("INSERT INTO game_history (player_id, result) VALUES (?, ?)", (player_id, result))
    conn.commit()
    conn.close()


def get_player_stats(player_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, wins, losses, games_played FROM players WHERE id = ?", (player_id,))
    name, wins, losses, games_played = cursor.fetchone()
    conn.close()

    win_rate = (wins / games_played * 100) if games_played > 0 else 0
    return name, wins, losses, games_played, round(win_rate, 2)

def get_top_players(limit=5):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            name,
            wins,
            losses,
            games_played,
            CASE WHEN games_played > 0 THEN ROUND((wins * 100.0) / games_played, 2) ELSE 0 END AS win_rate
        FROM players
        ORDER BY wins DESC, win_rate DESC, games_played DESC
        LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_recent_games(player_id, limit=8):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT gh.result, gh.date_played
        FROM game_history gh
        WHERE gh.player_id = ?
        ORDER BY gh.id DESC
        LIMIT ?
        """,
        (player_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def clear_root(root):
    for widget in root.winfo_children():
        widget.destroy()


class AuthView:
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success

        self.root.title("Guess The Word - Login")
        self.root.geometry("760x560")
        self.root.minsize(700, 520)
        self.root.configure(bg="#EAF2FF")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("AuthCard.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)
        style.configure("AuthForm.TFrame", background="#F4F8FF")
        style.configure("AuthTitle.TLabel", background="#FFFFFF", foreground="#17233A", font=("Segoe UI Semibold", 22))
        style.configure("AuthText.TLabel", background="#FFFFFF", foreground="#4F5F70", font=("Segoe UI", 10))
        style.configure("AuthFormText.TLabel", background="#F4F8FF", foreground="#314A67", font=("Segoe UI Semibold", 10))
        style.configure("AuthBtn.TButton", font=("Segoe UI Semibold", 10), padding=8, foreground="#FFFFFF", background="#2563EB")
        style.map("AuthBtn.TButton", background=[("active", "#1D4ED8")])

        card = ttk.Frame(root, style="AuthCard.TFrame")
        card.pack(fill="both", expand=True, padx=32, pady=32)

        ttk.Label(card, text="Welcome to Guess The Word", style="AuthTitle.TLabel").pack(anchor="center", pady=(24, 4))
        ttk.Label(card, text="Login with your account or create a new one.", style="AuthText.TLabel").pack(anchor="center", pady=(0, 16))

        form = ttk.Frame(card, style="AuthForm.TFrame")
        form.pack(fill="x", padx=28, pady=8)

        ttk.Label(form, text="Username", style="AuthFormText.TLabel").grid(row=0, column=0, sticky="w", pady=(12, 4), padx=14)
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(form, textvariable=self.username_var, width=34)
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=14)

        ttk.Label(form, text="Password", style="AuthFormText.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 4), padx=14)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(form, textvariable=self.password_var, show="*", width=34)
        self.password_entry.grid(row=3, column=0, sticky="ew", pady=(0, 10), padx=14)

        ttk.Label(form, text="Confirm Password (for Register)", style="AuthFormText.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 4), padx=14)
        self.confirm_var = tk.StringVar()
        self.confirm_entry = ttk.Entry(form, textvariable=self.confirm_var, show="*", width=34)
        self.confirm_entry.grid(row=5, column=0, sticky="ew", pady=(0, 12), padx=14)

        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(form, textvariable=self.status_var, style="AuthFormText.TLabel")
        self.status_label.grid(row=6, column=0, sticky="w", pady=(0, 12), padx=14)

        actions = ttk.Frame(card)
        actions.pack(pady=(2, 20))

        tk.Button(
            actions,
            text="Login",
            width=14,
            font=("Segoe UI Semibold", 10),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief="flat",
            command=self.handle_login,
        ).grid(row=0, column=0, padx=6)
        tk.Button(
            actions,
            text="Register",
            width=14,
            font=("Segoe UI Semibold", 10),
            bg="#0EA5A4",
            fg="#FFFFFF",
            activebackground="#0F766E",
            activeforeground="#FFFFFF",
            relief="flat",
            command=self.handle_register,
        ).grid(row=0, column=1, padx=6)

        self.username_entry.focus_set()

    def set_status(self, text, success=False):
        style_name = "AuthSuccess.TLabel" if success else "AuthError.TLabel"
        style = ttk.Style()
        style.configure("AuthSuccess.TLabel", background="#FFFFFF", foreground="#2C6E49", font=("Segoe UI", 10))
        style.configure("AuthError.TLabel", background="#FFFFFF", foreground="#AF3D3D", font=("Segoe UI", 10))
        self.status_label.configure(style=style_name)
        self.status_var.set(text)

    def validate_common(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if len(username) < 3:
            self.set_status("Username must be at least 3 characters.")
            return None, None
        if len(password) < 4:
            self.set_status("Password must be at least 4 characters.")
            return None, None
        return username, password

    def handle_login(self):
        username, password = self.validate_common()
        if not username:
            return

        player_id = authenticate_player(username, password)
        if player_id is None:
            self.set_status("Invalid username or password.")
            return

        self.set_status("Login successful.", success=True)
        self.on_login_success(player_id)

    def handle_register(self):
        username, password = self.validate_common()
        if not username:
            return

        confirm_password = self.confirm_var.get()
        if password != confirm_password:
            self.set_status("Password and confirm password do not match.")
            return

        player_id = register_player(username, password)
        if player_id is None:
            self.set_status("Username already exists. Try a different one.")
            return

        self.set_status("Registration successful. You are now logged in.", success=True)
        self.on_login_success(player_id)

# GUI Hangman Game#
class HangmanGame:
    def __init__(self, root, player_id, on_logout):
        self.root = root
        self.on_logout = on_logout
        self.root.title("Guess The Word - Modern Hangman")
        self.root.geometry("1220x800")
        self.root.minsize(1100, 720)
        self.root.configure(bg="#EAF2FF")

        self.player_id = player_id

        self.word_bank = {
            "Tech": ["python", "binary", "database", "network", "compiler", "variable", "algorithm", "interface"],
            "Nature": ["forest", "mountain", "thunder", "rainbow", "volcano", "ocean", "wildlife", "glacier"],
            "Career": ["engineer", "teacher", "doctor", "designer", "analyst", "manager", "architect", "researcher"],
            "Everyday": ["puzzle", "journey", "library", "kitchen", "holiday", "station", "backpack", "notebook"]
        }
        self.categories = ["All"] + list(self.word_bank.keys())
        self.difficulty_config = {
            "Easy": {"attempts": 10, "reveals": 3},
            "Medium": {"attempts": 8, "reveals": 2},
            "Hard": {"attempts": 6, "reveals": 1}
        }

        self.category_var = tk.StringVar(value="All")
        self.difficulty_var = tk.StringVar(value="Medium")

        self.chosen_word = ""
        self.display_word = []
        self.attempts = 0
        self.max_attempts = 0
        self.guessed_letters = set()
        self.round_seconds = 0
        self.streak = 0
        self.score = 0
        self.round_active = False
        self.alive = True
        self.timer_job = None

        self.configure_styles()
        self.build_layout()
        self.create_letter_buttons()
        self.refresh_player_panels()
        self.start_new_round()
        self.run_round_timer()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TopCard.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)
        style.configure("Panel.TFrame", background="#FFFFFF", relief="solid", borderwidth=1)
        style.configure("Header.TLabel", background="#FFFFFF", foreground="#0F2744", font=("Segoe UI Semibold", 24))
        style.configure("SubHeader.TLabel", background="#FFFFFF", foreground="#3E5C76", font=("Segoe UI", 11))
        style.configure("PanelTitle.TLabel", background="#FFFFFF", foreground="#16324F", font=("Segoe UI Semibold", 13))
        style.configure("Body.TLabel", background="#FFFFFF", foreground="#2A3B4F", font=("Segoe UI", 11))
        style.configure("Info.TLabel", background="#FFFFFF", foreground="#1E3A5F", font=("Segoe UI Semibold", 11))
        style.configure("TProgressbar", thickness=14)
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=7, foreground="#FFFFFF", background="#2563EB")
        style.map("Accent.TButton", background=[("active", "#1D4ED8")])
        style.configure("Warning.TButton", font=("Segoe UI Semibold", 10), padding=7, foreground="#102A43", background="#F59E0B")
        style.map("Warning.TButton", background=[("active", "#D97706")])
        style.configure("Danger.TButton", font=("Segoe UI Semibold", 10), padding=7, foreground="#FFFFFF", background="#DC2626")
        style.map("Danger.TButton", background=[("active", "#B91C1C")])

        style.configure("Custom.Treeview", rowheight=26, background="#F8FBFF", fieldbackground="#F8FBFF", foreground="#1F3552")
        style.configure("Custom.Treeview.Heading", font=("Segoe UI Semibold", 10), background="#DDEBFF", foreground="#14304D")
        style.map("Custom.Treeview", background=[("selected", "#60A5FA")], foreground=[("selected", "#0F172A")])

    def build_layout(self):
        top = ttk.Frame(self.root, style="TopCard.TFrame")
        top.pack(fill="x", padx=14, pady=(14, 8))

        header = ttk.Frame(top, style="TopCard.TFrame")
        header.pack(fill="x", padx=12, pady=10)
        ttk.Label(header, text="Modern Hangman Arena", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Choose category and difficulty, use hints smartly, and climb the leaderboard.",
            style="SubHeader.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        controls = ttk.Frame(top, style="TopCard.TFrame")
        controls.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Label(controls, text="Category:", style="Body.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.category_combo = ttk.Combobox(
            controls,
            textvariable=self.category_var,
            values=self.categories,
            state="readonly",
            width=16
        )
        self.category_combo.grid(row=0, column=1, padx=(0, 14))

        ttk.Label(controls, text="Difficulty:", style="Body.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.difficulty_combo = ttk.Combobox(
            controls,
            textvariable=self.difficulty_var,
            values=list(self.difficulty_config.keys()),
            state="readonly",
            width=12
        )
        self.difficulty_combo.grid(row=0, column=3, padx=(0, 14))

        tk.Button(
            controls,
            text="Start New Round",
            font=("Segoe UI Semibold", 10),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=6,
            command=self.start_new_round,
        ).grid(row=0, column=4, padx=(0, 10))
        tk.Button(
            controls,
            text="Use Hint (-1 attempt)",
            font=("Segoe UI Semibold", 10),
            bg="#F59E0B",
            fg="#102A43",
            activebackground="#D97706",
            activeforeground="#102A43",
            relief="flat",
            padx=12,
            pady=6,
            command=self.use_hint,
        ).grid(row=0, column=5)
        tk.Button(
            controls,
            text="Logout",
            font=("Segoe UI Semibold", 10),
            bg="#DC2626",
            fg="#FFFFFF",
            activebackground="#B91C1C",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=6,
            command=self.logout,
        ).grid(row=0, column=6, padx=(10, 0))

        self.main = ttk.Frame(self.root, style="Panel.TFrame")
        self.main.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.main.columnconfigure(0, weight=3)
        self.main.columnconfigure(1, weight=2)
        self.main.rowconfigure(0, weight=1)

        self.game_panel = ttk.Frame(self.main, style="Panel.TFrame")
        self.game_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.side_panel = ttk.Frame(self.main, style="Panel.TFrame")
        self.side_panel.grid(row=0, column=1, sticky="nsew")

        self.word_label = ttk.Label(self.game_panel, text="", style="PanelTitle.TLabel", font=("Consolas", 28))
        self.word_label.pack(anchor="center", pady=(20, 12))

        info_row = ttk.Frame(self.game_panel, style="Panel.TFrame")
        info_row.pack(fill="x", padx=14, pady=(0, 8))
        self.attempts_label = ttk.Label(info_row, text="Attempts: 0", style="Info.TLabel")
        self.attempts_label.grid(row=0, column=0, sticky="w")
        self.timer_label = ttk.Label(info_row, text="Round Time: 00:00", style="Info.TLabel")
        self.timer_label.grid(row=0, column=1, sticky="w", padx=18)
        self.score_label = ttk.Label(info_row, text="Score: 0 | Streak: 0", style="Info.TLabel")
        self.score_label.grid(row=0, column=2, sticky="w")

        self.attempt_progress = ttk.Progressbar(self.game_panel, mode="determinate")
        self.attempt_progress.pack(fill="x", padx=14, pady=(0, 12))

        self.keyboard_frame = ttk.Frame(self.game_panel, style="Panel.TFrame")
        self.keyboard_frame.pack(pady=4)

        self.status_label = ttk.Label(self.game_panel, text="", style="Body.TLabel")
        self.status_label.pack(pady=(10, 6))

        self.player_stats_label = ttk.Label(self.side_panel, text="", style="Body.TLabel", justify="left")
        self.player_stats_label.pack(anchor="w", padx=12, pady=(16, 10))

        ttk.Label(self.side_panel, text="Leaderboard", style="PanelTitle.TLabel").pack(anchor="w", padx=12)
        self.leaderboard = ttk.Treeview(self.side_panel, columns=("player", "wins", "wr"), show="headings", height=6, style="Custom.Treeview")
        self.leaderboard.heading("player", text="Player")
        self.leaderboard.heading("wins", text="Wins")
        self.leaderboard.heading("wr", text="Win %")
        self.leaderboard.column("player", width=110, anchor="w")
        self.leaderboard.column("wins", width=55, anchor="center")
        self.leaderboard.column("wr", width=65, anchor="center")
        self.leaderboard.pack(fill="x", padx=12, pady=(6, 14))

        ttk.Label(self.side_panel, text="Recent Games", style="PanelTitle.TLabel").pack(anchor="w", padx=12)
        self.recent_list = tk.Listbox(
            self.side_panel,
            height=10,
            relief="flat",
            bg="#F8FBFF",
            fg="#1F3552",
            selectbackground="#60A5FA",
            selectforeground="#0F172A",
            highlightthickness=1,
            highlightbackground="#C9DFFF",
            font=("Segoe UI", 10)
        )
        self.recent_list.pack(fill="both", expand=True, padx=12, pady=(6, 12))

    def create_letter_buttons(self):
        letters = "QWERTYUIOPASDFGHJKLZXCVBNM"
        self.letter_buttons = {}
        for idx, letter in enumerate(letters):
            btn = tk.Button(
                self.keyboard_frame,
                text=letter,
                width=4,
                height=2,
                font=("Segoe UI Semibold", 10),
                bg="#E0ECFF",
                fg="#12314E",
                relief="flat",
                activebackground="#C3D9FF",
                command=lambda l=letter: self.guess_letter(l)
            )
            row, col = divmod(idx, 9)
            btn.grid(row=row, column=col, padx=3, pady=3)
            self.letter_buttons[letter] = btn
            btn.bind("<Enter>", lambda _e, b=btn: self.on_key_hover(b, entering=True))
            btn.bind("<Leave>", lambda _e, b=btn: self.on_key_hover(b, entering=False))

    def on_key_hover(self, button, entering):
        if str(button.cget("state")) == "disabled":
            return
        button.configure(bg="#BFD4FF" if entering else "#E0ECFF")

    def choose_word(self):
        category = self.category_var.get()
        difficulty = self.difficulty_var.get()

        pool = []
        if category == "All":
            for words in self.word_bank.values():
                pool.extend(words)
        else:
            pool = list(self.word_bank.get(category, []))

        if difficulty == "Easy":
            filtered = [w for w in pool if len(w) <= 6]
        elif difficulty == "Medium":
            filtered = [w for w in pool if 6 <= len(w) <= 8]
        else:
            filtered = [w for w in pool if len(w) >= 8]

        chosen_pool = filtered if filtered else pool
        return random.choice(chosen_pool).upper()

    def start_new_round(self):
        settings = self.difficulty_config[self.difficulty_var.get()]
        self.max_attempts = settings["attempts"]
        self.attempts = self.max_attempts
        self.chosen_word = self.choose_word()
        self.display_word = ["_" for _ in self.chosen_word]
        self.guessed_letters = set()
        self.round_seconds = 0
        self.round_active = True

        reveal_count = min(settings["reveals"], len(self.chosen_word))
        reveal_indices = random.sample(range(len(self.chosen_word)), reveal_count)
        for idx in reveal_indices:
            self.display_word[idx] = self.chosen_word[idx]
            self.guessed_letters.add(self.chosen_word[idx])

        for letter, btn in self.letter_buttons.items():
            if letter in self.guessed_letters:
                btn.config(state="disabled", bg="#93C5FD", fg="#0F2A44")
            else:
                btn.config(state="normal", bg="#E0ECFF", fg="#12314E")

        self.status_label.config(text="Round started. Make your first guess.")
        self.refresh_round_ui()

    def refresh_round_ui(self):
        self.word_label.config(text=" ".join(self.display_word))
        self.attempts_label.config(text=f"Attempts: {self.attempts}/{self.max_attempts}")
        self.score_label.config(text=f"Score: {self.score} | Streak: {self.streak}")
        self.attempt_progress.configure(maximum=self.max_attempts, value=self.attempts)
        minutes, seconds = divmod(self.round_seconds, 60)
        self.timer_label.config(text=f"Round Time: {minutes:02d}:{seconds:02d}")

    def run_round_timer(self):
        if not self.alive:
            return

        if self.round_active:
            self.round_seconds += 1
            self.refresh_round_ui()
        self.timer_job = self.root.after(1000, self.run_round_timer)

    def disable_keyboard(self):
        for btn in self.letter_buttons.values():
            btn.config(state="disabled")

    def guess_letter(self, letter):
        if not self.round_active or letter in self.guessed_letters:
            return

        self.guessed_letters.add(letter)
        button = self.letter_buttons[letter]
        button.config(state="disabled")

        if letter in self.chosen_word:
            for idx, char in enumerate(self.chosen_word):
                if char == letter:
                    self.display_word[idx] = letter
            button.config(bg="#86EFAC", fg="#14532D")
            self.status_label.config(text=f"Good guess: '{letter}' is in the word.")
        else:
            self.attempts -= 1
            button.config(bg="#FCA5A5", fg="#7F1D1D")
            self.status_label.config(text=f"Nope: '{letter}' is not in the word.")

        self.refresh_round_ui()
        self.check_round_end()

    def use_hint(self):
        if not self.round_active:
            return
        if self.attempts <= 1:
            self.status_label.config(text="Hint unavailable. You need at least 2 attempts.")
            return

        hidden_letters = sorted({
            self.chosen_word[idx]
            for idx, char in enumerate(self.display_word)
            if char == "_"
        })

        if not hidden_letters:
            self.status_label.config(text="No hint needed. The word is already complete.")
            return

        hint_letter = random.choice(hidden_letters)
        self.guessed_letters.add(hint_letter)
        self.attempts -= 1

        for idx, char in enumerate(self.chosen_word):
            if char == hint_letter:
                self.display_word[idx] = hint_letter

        btn = self.letter_buttons.get(hint_letter)
        if btn is not None:
            btn.config(state="disabled", bg="#FCD34D", fg="#5F370E")

        self.status_label.config(text=f"Hint revealed letter '{hint_letter}'. -1 attempt.")
        self.refresh_round_ui()
        self.check_round_end()

    def check_round_end(self):
        if "_" not in self.display_word:
            self.end_round(win=True)
        elif self.attempts <= 0:
            self.end_round(win=False)

    def end_round(self, win):
        self.round_active = False
        self.disable_keyboard()

        if win:
            self.streak += 1
            self.score += (self.attempts * 10) + 25
            update_stats(self.player_id, "win")
            self.status_label.config(text=f"You won this round in {self.round_seconds}s.")
            messagebox.showinfo("Round Result", "Great job. You solved the word.")
        else:
            self.streak = 0
            self.score = max(0, self.score - 15)
            update_stats(self.player_id, "loss")
            self.status_label.config(text=f"Round lost. The word was {self.chosen_word}.")
            messagebox.showinfo("Round Result", f"Round over. The word was: {self.chosen_word}")

        self.refresh_player_panels()
        self.refresh_round_ui()
        self.start_new_round()

    def refresh_player_panels(self):
        name, wins, losses, games_played, win_rate = get_player_stats(self.player_id)
        self.player_stats_label.config(
            text=(
                f"Player: {name}\n"
                f"Games: {games_played}\n"
                f"Wins: {wins} | Losses: {losses}\n"
                f"Win Rate: {win_rate}%"
            )
        )

        for row in self.leaderboard.get_children():
            self.leaderboard.delete(row)
        for player_name, pwins, _, _, pwin_rate in get_top_players(limit=5):
            self.leaderboard.insert("", "end", values=(player_name, pwins, f"{pwin_rate}%"))

        self.recent_list.delete(0, tk.END)
        recent_games = get_recent_games(self.player_id, limit=10)
        if not recent_games:
            self.recent_list.insert(tk.END, "No games played yet.")
            return

        for result, date_played in recent_games:
            self.recent_list.insert(tk.END, f"{date_played} | {result.upper()}")

    def logout(self):
        confirm = messagebox.askyesno("Logout", "Do you want to logout and return to login screen?")
        if not confirm:
            return
        self.cleanup()
        self.on_logout()

    def cleanup(self):
        self.alive = False
        self.round_active = False
        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None


class GameApp:
    def __init__(self, root):
        self.root = root
        self.active_game = None
        self.show_auth()

    def show_auth(self):
        clear_root(self.root)
        self.active_game = None
        AuthView(self.root, self.start_game_for_player)

    def start_game_for_player(self, player_id):
        clear_root(self.root)
        self.active_game = HangmanGame(self.root, player_id, self.show_auth)

# main
def start_game():
    setup_database()
    root = tk.Tk()
    GameApp(root)
    root.mainloop()

if __name__ == "__main__":
    start_game()
