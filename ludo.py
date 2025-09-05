class Token:
    def __init__(self, player, idx):
        self.player = player
        self.idx = idx
        self.position = -1  # -1 means at home
        self.finished = False
import tkinter as tk
from tkinter import filedialog
import random
import threading
import time
import json
try:
    from PIL import Image, ImageDraw, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageDraw = None
    ImageTk = None
try:
    import winsound
    SOUND_ENABLED = True
except ImportError:
    SOUND_ENABLED = False

BOARD_SIZE = 15
CELL_SIZE = 30
PLAYER_COLORS = ["red", "green", "yellow", "blue"]
NUM_TOKENS = 4
SAFE_CELLS = [
    (1, 6), (1, 8), (6, 1), (8, 1), (13, 6), (13, 8), (6, 13), (8, 13),
    (6, 6), (6, 8), (8, 6), (8, 8)
]
START_POSITIONS = [(1, 1), (1, 13), (13, 1), (13, 13)]
ENTRY_CELLS = [(2, 6), (8, 2), (6, 12), (12, 8)]
HOME_PATHS = [
    [(i, 7) for i in range(1, 7)],
    [(7, i) for i in range(1, 7)],
    [(i, 7) for i in range(13, 7, -1)],
    [(7, i) for i in range(13, 7, -1)]
]

def get_main_path():
    # Returns the main path as a list of (x, y) tuples in order
    path = []
    # Top row left to right
    for i in range(1, 6):
        path.append((i, 6))
    # Down right column
    for i in range(6, 0, -1):
        path.append((6, i))
    # Left to right bottom row
    for i in range(6, 14):
        path.append((i, 1))
    # Up right column
    for i in range(2, 7):
        path.append((8, i))
    # Right to left bottom row
    for i in range(8, 14):
        path.append((i, 6))
    # Up left column
    for i in range(6, 14):
        path.append((14, i))
    # Right to left top row
    for i in range(14, 8, -1):
        path.append((i, 8))
    # Down left column
    for i in range(8, 14):
        path.append((8, i))
    # Left to right top row
    for i in range(8, 1, -1):
        path.append((6, i))
    # Up left column
    for i in range(8, 1, -1):
        path.append((i, 8))
    return path

MAIN_PATH = get_main_path()

class LudoGame:
    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Game Settings")
        entries = []
        color_entries = []
        for i in range(self.num_players):
            tk.Label(settings_win, text=f"Player {i+1} Name:").grid(row=i, column=0)
            name_var = tk.StringVar(value=self.player_names[i])
            entry = tk.Entry(settings_win, textvariable=name_var)
            entry.grid(row=i, column=1)
            entries.append(name_var)
            tk.Label(settings_win, text=f"Color:").grid(row=i, column=2)
            color_var = tk.StringVar(value=self.player_colors[i])
            color_entry = tk.Entry(settings_win, textvariable=color_var)
            color_entry.grid(row=i, column=3)
            color_entries.append(color_var)
        def save_settings():
            for i in range(self.num_players):
                self.player_names[i] = entries[i].get()
                self.player_colors[i] = color_entries[i].get()
            self.update_board()
            self.update_info()
            self.update_finished_tokens()
            settings_win.destroy()
        tk.Button(settings_win, text="Save", command=save_settings).grid(row=self.num_players, column=0, columnspan=4, pady=10)
    def __init__(self, root, num_players=2, player_names=None, player_colors=None, ai_players=None):
        self.root = root
        self.num_players = num_players
        self.current_player = 0
        self.tokens = [[Token(i, j) for j in range(NUM_TOKENS)] for i in range(num_players)]
        self.canvas = None
        self.token_drawings = {}
        self.dice_label = None
        self.roll_button = None
        self.info_label = None
        self.finished_label = None
        self.dice_value = 0
        self.player_names = player_names if player_names else [f"Player {i+1}" for i in range(num_players)]
        self.player_colors = player_colors if player_colors else PLAYER_COLORS[:num_players]
        # Placeholder player icon images
        self.player_images = []
        if PIL_AVAILABLE:
            icon_colors = self.player_colors
            for color in icon_colors:
                img = Image.new("RGBA", (20, 20), (0,0,0,0))
                draw = ImageDraw.Draw(img)
                draw.ellipse((2,2,18,18), fill=color, outline="black")
                self.player_images.append(ImageTk.PhotoImage(img))
            # Placeholder dice faces
            self.dice_faces = []
            for i in range(1, 7):
                img = Image.new("RGBA", (40, 40), "white")
                draw = ImageDraw.Draw(img)
                draw.rectangle((0,0,39,39), outline="black", width=2)
                # Draw dots for dice face
                dot = lambda x, y: draw.ellipse((x-4, y-4, x+4, y+4), fill="black")
                if i in [1,3,5]: dot(20,20)
                if i >= 2: dot(10,10); dot(30,30)
                if i >= 4: dot(10,30); dot(30,10)
                if i == 6: dot(10,20); dot(30,20)
                self.dice_faces.append(ImageTk.PhotoImage(img))
        else:
            self.player_images = [None]*self.num_players
            self.dice_faces = [None]*6
        # Create the board and controls on startup
        self.create_board()
        self.create_controls()

    def create_board(self):
        self.canvas = tk.Canvas(self.root, width=BOARD_SIZE*CELL_SIZE, height=BOARD_SIZE*CELL_SIZE, bg="white")
        self.canvas.grid(row=0, column=0, columnspan=3)
        for i in range(BOARD_SIZE+1):
            self.canvas.create_line(i*CELL_SIZE, 0, i*CELL_SIZE, BOARD_SIZE*CELL_SIZE, fill="gray")
            self.canvas.create_line(0, i*CELL_SIZE, BOARD_SIZE*CELL_SIZE, i*CELL_SIZE, fill="gray")
        # Draw safe cells
        for x, y in SAFE_CELLS:
            self.canvas.create_rectangle(x*CELL_SIZE, y*CELL_SIZE, (x+1)*CELL_SIZE, (y+1)*CELL_SIZE, fill="#cccccc")
        # Draw home areas
        for i, (x, y) in enumerate(START_POSITIONS):
            self.canvas.create_rectangle(x*CELL_SIZE, y*CELL_SIZE, (x+2)*CELL_SIZE, (y+2)*CELL_SIZE, fill=self.player_colors[i])
        # Draw entry cells
        for x, y in ENTRY_CELLS:
            self.canvas.create_rectangle(x*CELL_SIZE, y*CELL_SIZE, (x+1)*CELL_SIZE, (y+1)*CELL_SIZE, fill="#888888")

    def create_controls(self):
        self.dice_label = tk.Label(self.root, text="Roll the dice!", font=("Arial", 16))
        self.dice_label.grid(row=1, column=0, pady=10)
        self.roll_button = tk.Button(self.root, text="Roll Dice", font=("Arial", 14), command=self.roll_dice)
        self.roll_button.grid(row=1, column=1, pady=10)
        self.save_button = tk.Button(self.root, text="Save Game", font=("Arial", 12), command=self.save_game)
        self.save_button.grid(row=1, column=2, padx=5)
        self.load_button = tk.Button(self.root, text="Load Game", font=("Arial", 12), command=self.load_game)
        self.load_button.grid(row=1, column=3, padx=5)
        self.undo_button = tk.Button(self.root, text="Undo", font=("Arial", 12), command=self.undo)
        self.undo_button.grid(row=1, column=4, padx=5)
        self.redo_button = tk.Button(self.root, text="Redo", font=("Arial", 12), command=self.redo)
        self.redo_button.grid(row=1, column=5, padx=5)

    def undo(self):
        if not self.history:
            self.info_label.config(text="Nothing to undo.")
            return
        state = self.pop_history()
        self.future.append({
            'current_player': self.current_player,
            'tokens': [
                [{'position': t.position, 'finished': t.finished} for t in player_tokens]
                for player_tokens in self.tokens
            ]
        })
        self.restore_state(state)
        self.info_label.config(text="Undo performed.")

    def redo(self):
        if not self.future:
            self.info_label.config(text="Nothing to redo.")
            return
        state = self.future.pop()
        self.push_history()
        self.restore_state(state)
        self.info_label.config(text="Redo performed.")

    def save_game(self):
        data = {
            'current_player': self.current_player,
            'tokens': [
                [{'position': t.position, 'finished': t.finished} for t in player_tokens]
                for player_tokens in self.tokens
            ],
            'player_names': self.player_names,
            'player_colors': self.player_colors,
            'num_players': self.num_players
        }
        file_path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON Files', '*.json')])
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(data, f)
            self.info_label.config(text="Game saved!")

    def load_game(self):
        file_path = filedialog.askopenfilename(filetypes=[('JSON Files', '*.json')])
        if file_path:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.current_player = data.get('current_player', 0)
            for p, player_tokens in enumerate(data['tokens']):
                for t, tdata in enumerate(player_tokens):
                    self.tokens[p][t].position = tdata['position']
                    self.tokens[p][t].finished = tdata['finished']
            self.player_names = data.get('player_names', self.player_names)
            self.player_colors = data.get('player_colors', self.player_colors)
            self.num_players = data.get('num_players', self.num_players)
            self.update_board()
            self.update_info()
            self.update_finished_tokens()
            self.info_label.config(text="Game loaded!")

    def update_info(self):
        self.info_label.config(text=f"{self.player_names[self.current_player]}'s turn ({self.player_colors[self.current_player]})")
        # If it's an AI player's turn, let the AI play automatically
        if self.ai_players[self.current_player]:
            self.root.after(800, self.ai_play)

    def ai_play(self):
        # AI rolls dice and makes a move
        self.roll_dice()
        movable = self.get_movable_tokens()
        if movable:
            chosen = random.choice(movable)
            self.move_token(chosen)
    def update_finished_tokens(self):
        finished_counts = [sum(1 for t in self.tokens[p] if t.finished) for p in range(self.num_players)]
        text = " | ".join(f"{self.player_names[p]}: {finished_counts[p]}/{NUM_TOKENS} finished" for p in range(self.num_players))
        self.finished_label.config(text=text)

    def roll_dice(self):
        self.dice_value = random.randint(1, 6)
        self.animate_dice(self.dice_value)
        if SOUND_ENABLED:
            threading.Thread(target=lambda: winsound.MessageBeep()).start()
        movable = self.get_movable_tokens()
        if not movable:
            self.info_label.config(text=f"No valid moves for {self.player_names[self.current_player]}. Skipping turn.")
            self.root.after(1200, self.next_player)
            return
        self.show_token_options()
    def animate_dice(self, final_value):
        import random
        if PIL_AVAILABLE and all(self.dice_faces):
            for _ in range(10):
                val = random.randint(1, 6)
                self.dice_label.config(image=self.dice_faces[val-1], text="")
                self.root.update()
                time.sleep(0.07)
            self.dice_label.config(image=self.dice_faces[final_value-1], text="")
        else:
            for _ in range(10):
                val = random.randint(1, 6)
                self.dice_label.config(text=f"Rolling... {val}")
                self.root.update()
                time.sleep(0.07)
            self.dice_label.config(text=f"{self.player_names[self.current_player]} rolled: {final_value}")

    def show_token_options(self):
        movable = self.get_movable_tokens()
        self.info_label.config(text=f"{self.player_names[self.current_player]}: Click a token to move")
        for token in movable:
            self.highlight_token(token)

    def get_movable_tokens(self):
        player_tokens = self.tokens[self.current_player]
        movable = []
        for token in player_tokens:
            if token.finished:
                continue
            if token.position == -1 and self.dice_value == 6:
                movable.append(token)
            elif token.position >= 0 and not token.finished:
                if token.position + self.dice_value <= len(MAIN_PATH) + len(HOME_PATHS[self.current_player]) - 1:
                    movable.append(token)
        return movable

    def highlight_token(self, token):
        coords = self.get_token_coords(token)
        if coords:
            x, y = coords
            oval = self.canvas.create_oval(
                x*CELL_SIZE+10, y*CELL_SIZE+10, (x+1)*CELL_SIZE-10, (y+1)*CELL_SIZE-10,
                outline="black", width=4
            )
            self.canvas.tag_bind(oval, "<Button-1>", lambda e, t=token: self.move_token(t))
            self.token_drawings[(token.player, token.idx, "highlight")] = oval

    def get_token_coords(self, token):
        if token.position == -1:
            # Home area
            x, y = START_POSITIONS[token.player]
            return x + (token.idx % 2), y + (token.idx // 2)
        elif token.position < len(MAIN_PATH):
            return MAIN_PATH[(token.position + 13*token.player) % len(MAIN_PATH)]
        else:
            # Home path
            home_idx = token.position - len(MAIN_PATH)
            if home_idx < len(HOME_PATHS[token.player]):
                return HOME_PATHS[token.player][home_idx]
        return None

    def move_token(self, token):
        self.push_history()
        # Remove highlights
        for key in list(self.token_drawings):
            if len(key) == 3 and key[2] == "highlight":
                self.canvas.delete(self.token_drawings[key])
                del self.token_drawings[key]
        if token.position == -1:
            self.animate_token(token, 0)
        else:
            self.animate_token(token, token.position + self.dice_value)

    def animate_token(self, token, target_pos):
        # Disable undo/redo during animation
        self.undo_button.config(state=tk.DISABLED)
        self.redo_button.config(state=tk.DISABLED)
        # Animate token movement step by step
        def do_animation():
            pos = token.position if token.position >= 0 else -1
            steps = (target_pos - pos) if pos >= 0 else 1
            for _ in range(steps):
                if pos == -1:
                    pos = 0
                else:
                    pos += 1
                token.position = pos
                self.update_board()
                time.sleep(0.15)
            # Check for finish
            if token.position == len(MAIN_PATH) + len(HOME_PATHS[self.current_player]) - 1:
                token.finished = True
                self.info_label.config(text=f"{self.player_names[self.current_player]} finished a token!")
                if SOUND_ENABLED:
                    winsound.MessageBeep(440)
            captured = self.capture_tokens(token)
            self.update_board()
            self.update_finished_tokens()
            if self.check_win():
                self.info_label.config(text=f"{self.player_names[self.current_player]} wins!")
                self.roll_button.config(state=tk.DISABLED)
                if SOUND_ENABLED:
                    winsound.MessageBeep(880)
            elif self.dice_value == 6:
                self.info_label.config(text=f"{self.player_names[self.current_player]} rolled a 6! Go again.")
            else:
                self.root.after(1000, self.next_player)
            # Re-enable undo/redo after animation
            self.undo_button.config(state=tk.NORMAL)
            self.redo_button.config(state=tk.NORMAL)
            if captured and SOUND_ENABLED:
                winsound.MessageBeep(220)
        threading.Thread(target=do_animation).start()

    def capture_tokens(self, moved_token):
        moved_coords = self.get_token_coords(moved_token)
        if moved_coords in SAFE_CELLS:
            return False
        captured = False
        for p, player_tokens in enumerate(self.tokens):
            if p == self.current_player:
                continue
            for token in player_tokens:
                if not token.finished and token.position >= 0 and self.get_token_coords(token) == moved_coords:
                    token.position = -1  # Send home
                    captured = True
        return captured

    def update_board(self):
        # Remove all token drawings
        for key in list(self.token_drawings):
            self.canvas.delete(self.token_drawings[key])
            del self.token_drawings[key]
        # Draw tokens with better graphics (rounded, shadow, icon image if available)
        for p, player_tokens in enumerate(self.tokens):
            for t in player_tokens:
                coords = self.get_token_coords(t)
                if coords:
                    x, y = coords
                    # Draw shadow
                    shadow = self.canvas.create_oval(
                        x*CELL_SIZE+8, y*CELL_SIZE+8, (x+1)*CELL_SIZE-2, (y+1)*CELL_SIZE-2,
                        fill="#222222", outline="", width=0
                    )
                    oval = self.canvas.create_oval(
                        x*CELL_SIZE+5, y*CELL_SIZE+5, (x+1)*CELL_SIZE-5, (y+1)*CELL_SIZE-5,
                        fill=self.player_colors[p], outline="black", width=2
                    )
                    if PIL_AVAILABLE and self.player_images[p]:
                        icon = self.canvas.create_image(
                            x*CELL_SIZE+CELL_SIZE//2, y*CELL_SIZE+CELL_SIZE//2, image=self.player_images[p]
                        )
                    else:
                        icon = self.canvas.create_text(
                            x*CELL_SIZE+CELL_SIZE//2, y*CELL_SIZE+CELL_SIZE//2,
                            text=self.player_names[p][0].upper(), fill="white", font=("Arial", 14, "bold")
                        )
                    self.token_drawings[(p, t.idx, "shadow")] = shadow
                    self.token_drawings[(p, t.idx)] = oval
                    self.token_drawings[(p, t.idx, "icon")] = icon

    def next_player(self):
        self.current_player = (self.current_player + 1) % self.num_players
        self.update_info()
        self.dice_label.config(text="Roll the dice!")

    def check_win(self):
        return all(token.finished for token in self.tokens[self.current_player])

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Ludo Game - Improved")
    num_players = 2  # Change to 3 or 4 for more players
    player_names = ["Alice", "Bot"]  # Player 2 is AI
    player_colors = ["#e74c3c", "#27ae60"]  # Customize colors (red, green)
    ai_players = [False, True]  # Player 2 is AI
    game = LudoGame(root, num_players=num_players, player_names=player_names, player_colors=player_colors, ai_players=ai_players)
    root.mainloop()