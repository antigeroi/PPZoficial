import sqlite3
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.db_path = os.environ.get('DATABASE_URL', 'ppz_bot.db')
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER UNIQUE,
                      username TEXT,
                      password TEXT,
                      nickname TEXT UNIQUE,
                      crypto_wallet TEXT,
                      balance REAL DEFAULT 0.0,
                      is_admin INTEGER DEFAULT 0,
                      is_banned INTEGER DEFAULT 0,
                      muted_until TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS rooms
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT UNIQUE,
                      owner_id INTEGER,
                      is_ephemeral INTEGER DEFAULT 0,
                      is_private INTEGER DEFAULT 0,
                      password TEXT,
                      created_at TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      room_id INTEGER,
                      user_id INTEGER,
                      message_text TEXT,
                      timestamp TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS pending_payments
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      amount REAL,
                      payment_type TEXT,
                      details TEXT,
                      created_at TEXT,
                      is_completed INTEGER DEFAULT 0)''')
        
        try:
            c.execute("INSERT OR IGNORE INTO users (user_id, username, password, nickname, crypto_wallet, is_admin, balance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (8097784914, 'admin', 'admin', 'admin', 'admin_wallet', 1, 1000.0))
        except:
            pass
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, password, nickname, crypto_wallet):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (user_id, username, password, nickname, crypto_wallet) VALUES (?, ?, ?, ?, ?)",
                     (user_id, username, password, nickname, crypto_wallet))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_user(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        return user
    
    def get_user_by_nickname(self, nickname):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE nickname=?", (nickname,))
        user = c.fetchone()
        conn.close()
        return user
    
    def update_balance(self, user_id, amount):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        conn.commit()
        conn.close()
    
    def transfer_balance(self, from_user_id, to_user_id, amount):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT balance FROM users WHERE user_id=?", (from_user_id,))
        sender_balance = c.fetchone()[0]
        
        if sender_balance >= amount:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, from_user_id))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, to_user_id))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    
    def get_all_users(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        conn.close()
        return users
    
    def ban_user(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
    
    def mute_user(self, user_id, mute_duration_minutes):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        muted_until = (datetime.now() + timedelta(minutes=mute_duration_minutes)).isoformat()
        c.execute("UPDATE users SET muted_until=? WHERE user_id=?", (muted_until, user_id))
        conn.commit()
        conn.close()
    
    def is_muted(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT muted_until FROM users WHERE user_id=?", (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            muted_until = datetime.fromisoformat(result[0])
            return datetime.now() < muted_until
        return False
    
    def create_room(self, name, owner_id, is_ephemeral, is_private, password):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            created_at = datetime.now().isoformat()
            c.execute("INSERT INTO rooms (name, owner_id, is_ephemeral, is_private, password, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                     (name, owner_id, is_ephemeral, is_private, password, created_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_rooms(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM rooms")
        rooms = c.fetchall()
        conn.close()
        return rooms
    
    def get_room(self, room_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM rooms WHERE id=?", (room_id,))
        room = c.fetchone()
        conn.close()
        return room
    
    def add_message(self, room_id, user_id, message_text):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute("INSERT INTO messages (room_id, user_id, message_text, timestamp) VALUES (?, ?, ?, ?)",
                 (room_id, user_id, message_text, timestamp))
        conn.commit()
        conn.close()
    
    def add_pending_payment(self, user_id, amount, payment_type, details):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            created_at = datetime.now().isoformat()
            c.execute("INSERT INTO pending_payments (user_id, amount, payment_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                     (user_id, amount, payment_type, details, created_at))
            conn.commit()
            return c.lastrowid
        except:
            return None
        finally:
            conn.close()
    
    def complete_payment(self, payment_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("UPDATE pending_payments SET is_completed=1 WHERE id=?", (payment_id,))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()
    
    def get_pending_payment(self, payment_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM pending_payments WHERE id=?", (payment_id,))
        payment = c.fetchone()
        conn.close()
        return payment
    
    def make_admin(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
