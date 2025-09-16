import random
import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog

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

    conn.commit()
    conn.close()

def get_player_id(player_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM players WHERE name = ?", (player_name,))
    player = cursor.fetchone()

    if player:
        player_id = player[0]
    else:
        cursor.execute("INSERT INTO players (name) VALUES (?)", (player_name,))
        conn.commit()
        player_id = cursor.lastrowid

    conn.close()
    return player_id

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

# GUI Hangman Game#
class HangmanGame:
    def __init__(self, root, player_id):
        self.root = root
        self.root.title("Guess The Word Game")

        self.player_id = player_id
        self.words = ['engineer', 'doctor', 'teacher', 'life', 'dog', 'animal', 'hunting', 'python', 'anoying']
        self.chosen_word = random.choice(self.words).upper()
        self.display_word = ["_" for _ in self.chosen_word]
        self.attempts = 8
        self.guessed_letters = set()

        idx1, idx2 = random.sample(range(len(self.display_word)), 2)
        self.display_word[idx1] = self.chosen_word[idx1]
        self.display_word[idx2] = self.chosen_word[idx2]

        self.label_word = tk.Label(root, text=" ".join(self.display_word), font=("Arial", 20))
        self.label_word.pack(pady=10)

        self.label_attempts = tk.Label(root, text=f"Attempts Left: {self.attempts}", font=("Arial", 14))
        self.label_attempts.pack(pady=5)

        self.letter_buttons = {}
        self.create_letter_buttons()

        self.stats_label = tk.Label(root, text="", font=("Arial", 12))
        self.stats_label.pack(pady=10)

        self.update_player_state()

    def create_letter_buttons(self):
        letters = "QWERTYUIOPASDFGHJKLZXCVBNM"
        button_frame = tk.Frame(self.root)
        button_frame.pack()

        for letter in letters:
            btn = tk.Button(button_frame, text=letter, width=4, height=2, command=lambda l=letter: self.guess_letter(l))
            btn.grid(row=letters.index(letter) // 9, column=letters.index(letter) % 9)
            self.letter_buttons[letter] = btn

    def guess_letter(self, letter):
        if letter in self.guessed_letters:
            return

        self.guessed_letters.add(letter)
        if letter in self.chosen_word:
            for i in range(len(self.chosen_word)):
                if self.chosen_word[i] == letter:
                    self.display_word[i] = letter
        else:
            self.attempts -= 1

        self.label_word.config(text=" ".join(self.display_word))
        self.label_attempts.config(text=f"Attempts Left: {self.attempts}")

        if "_" not in self.display_word:
            messagebox.showinfo("Hangman", "you've guessed it GOD DAMN RIGHT !!")
            update_stats(self.player_id, "win")
            self.update_player_state()
            self.reset_game()

        elif self.attempts == 0:
            messagebox.showinfo("Hangman", f"Wrong Guess ! The word was: {self.chosen_word}")
            update_stats(self.player_id, "loss")
            self.update_player_state()
            self.reset_game()

    def update_player_state(self):
        name, wins, losses, games_played, win_rate = get_player_stats(self.player_id)
        self.stats_label.config(text=f"Player: {name} | Wins: {wins} | Losses: {losses} | Games Played: {games_played} | Win Rate: {win_rate}%")

    def reset_game(self):
        self.chosen_word = random.choice(self.words).upper()
        self.display_word = ["_" for _ in self.chosen_word]
        self.attempts = 8
        self.guessed_letters = set()

        idx1, idx2 = random.sample(range(len(self.display_word)), 2)
        self.display_word[idx1] = self.chosen_word[idx1]
        self.display_word[idx2] = self.chosen_word[idx2]

        self.label_word.config(text=" ".join(self.display_word))
        self.label_attempts.config(text=f"Attempts Left: {self.attempts}")

        for btn in self.letter_buttons.values():
            btn.config(state="normal")

# main
def start_game():
    setup_database()
    root = tk.Tk()
    player_name = simpledialog.askstring("Enter Name", "Enter your name:")
    if not player_name:
        return
    player_id = get_player_id(player_name)
    HangmanGame(root, player_id)
    root.mainloop()

if __name__ == "__main__":
    start_game()
