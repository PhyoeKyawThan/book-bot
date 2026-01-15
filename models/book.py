from typing import Optional, List, Dict, Any
import json
from db import get_db
import sqlite3

class Book:
    def __init__(
        self,
        id: Optional[int] = None,
        title: Optional[str] = None,
        authors: Optional[List[str]] = None,
        summary: Optional[str] = None,
        subjects: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        formats: Optional[Dict] = None,
        price: Optional[int] = None,
        cover: Optional[str] = None,
        stock: Optional[int] = None
    ):
        self.id = id
        self.title = title
        self.authors = authors or []
        self.summary = summary
        self.subjects = subjects or []
        self.languages = languages or []
        self.formats = formats or {}
        self.price = price or 0
        self.cover = cover or ""
        self.stock = stock or 0

    @classmethod
    def toBook(cls, book_dict: dict) -> "Book":
        authors = book_dict['authors']

        summaries = book_dict.get("summaries", [])
        summary = summaries[0] if summaries else None

        return cls(
            id=book_dict.get("id"),
            title=book_dict.get("title"),
            authors=authors,
            summary=summary,
            subjects=book_dict.get("subjects", []),
            languages=book_dict.get("languages", []),
            formats=book_dict.get("formats", {}),
            price=book_dict.get("price", 0),
            cover=book_dict.get("cover", ""),
            stock=book_dict.get("stock", 0)
        )

    def __str__(self):
        return f"{self.title} by {', '.join(self.authors)}"

    # CRUD Operations
    @staticmethod
    def create(book: "Book") -> int:
        """Create a new book and return its ID"""
        db = get_db()
        
        cursor = db.execute('''
            INSERT INTO books (title, summary, authors, subjects, languages, formats, price, cover, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            book.title,
            book.summary,
            json.dumps(book.authors),
            json.dumps(book.subjects),
            json.dumps(book.languages),
            json.dumps(book.formats),
            book.price,
            book.cover,
            book.stock
        ))
        
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(book_id: int) -> Optional["Book"]:
        """Get a book by ID"""
        db = get_db()
        
        row = db.execute('''
            SELECT * FROM books WHERE id = ?
        ''', (book_id,)).fetchone()
        
        if row is None:
            return None
        
        return Book.from_row(row)

    @staticmethod
    def get_all(limit: int = 100, offset: int = 0) -> List["Book"]:
        """Get all books with pagination"""
        db = get_db()
        
        rows = db.execute('''
            SELECT * FROM books 
            ORDER BY id 
            LIMIT ? OFFSET ?
        ''', (limit, offset)).fetchall()
        
        return [Book.from_row(row) for row in rows]

    @staticmethod
    def search(
        title: Optional[str] = None,
        author: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50
    ) -> List["Book"]:
        """Search books by title, author, or subject"""
        db = get_db()
        
        query = "SELECT * FROM books WHERE 1=1"
        params = []
        
        if title:
            query += " AND LOWER(title) LIKE LOWER(?)"
            params.append(f"%{title}%")
        
        if author:
            query += " AND EXISTS (SELECT 1 FROM json_each(authors) WHERE value LIKE ?)"
            params.append(f"%{author}%")
        
        if subject:
            query += " AND EXISTS (SELECT 1 FROM json_each(subjects) WHERE value LIKE ?)"
            params.append(f"%{subject}%")
        
        query += " LIMIT ?"
        params.append(limit)
        
        rows = db.execute(query, params).fetchall()
        return [Book.from_row(row) for row in rows]

    @staticmethod
    def update(book: "Book") -> bool:
        """Update an existing book"""
        db = get_db()
        
        cursor = db.execute('''
            UPDATE books 
            SET title = ?, summary = ?, authors = ?, subjects = ?, languages = ?, formats = ?, stock = ?, price = ?
            WHERE id = ?
        ''', (
            book.title,
            book.summary,
            json.dumps(book.authors),
            json.dumps(book.subjects),
            json.dumps(book.languages),
            json.dumps(book.formats),
            book.id
        ))
        
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def delete(book_id: int) -> bool:
        """Delete a book by ID"""
        db = get_db()
        
        cursor = db.execute('''
            DELETE FROM books WHERE id = ?
        ''', (book_id,))
        
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def count() -> int:
        """Count total number of books"""
        db = get_db()
        
        result = db.execute('SELECT COUNT(*) as count FROM books').fetchone()
        return result['count']

    @staticmethod
    def from_row(row: sqlite3.Row) -> "Book":
        """Create a Book object from a database row"""
        print(row['authors'])
        return Book(
            id=row['id'],
            title=row['title'],
            summary=row['summary'],
            authors=json.loads(row['authors']) if row['authors'] else [],
            subjects=json.loads(row['subjects']) if row['subjects'] else [],
            languages=json.loads(row['languages']) if row['languages'] else [],
            formats=json.loads(row['formats']) if row['formats'] else {},
            price=row['price'],
            cover=row['cover'],
            stock=row['stock']
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Book object to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'authors': self.authors,
            'summary': self.summary,
            'subjects': self.subjects,
            'languages': self.languages,
            'formats': self.formats,
            'price': self.price,
            'cover': self.cover,
            'stock': self.stock
        }
    def calculate_shipping_time(self) -> str:
        """Calculate shipping time based on stock and formats"""
        if self.stock > 0:
            if 'ebook' in self.formats or 'pdf' in self.formats or 'epub' in self.formats:
                return "instant digital delivery"
            elif self.stock >= 10:
                return "2-3 business days"
            else:
                return "3-5 business days"
        else:
            return "currently out of stock (2-3 weeks backorder)"

    def get_formats_available(self) -> List[str]:
        """Get list of available formats"""
        return list(self.formats.keys()) if self.formats else []