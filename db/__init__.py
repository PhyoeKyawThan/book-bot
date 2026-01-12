import sqlite3
from flask import g
DATABASE = 'books.db'

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(callback: any = None):
    """Initialize the database with required tables"""
    db = get_db()
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            summary TEXT,
            authors TEXT,  -- JSON array
            subjects TEXT, -- JSON array
            languages TEXT, -- JSON array
            formats TEXT,   -- JSON object
            price INT, 
            stock INT
        )
    ''')
    if callback:
        callback()
    db.commit()

