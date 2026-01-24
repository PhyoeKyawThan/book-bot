import nltk
import re
from typing import List, Dict, Optional, Tuple
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from db import get_db
from models.book import Book
from nltk.stem import WordNetLemmatizer
from flask import session

# Download NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
    nltk.data.find('punkt_tab')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')
    nltk.download('punkt_tab')


# Initialize NLTK tools
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

# Chatbot Intelligence Class
class BookChatbot:
    def __init__(self):
        self.intent_keywords = {
            'price': ['price', 'cost', 'worth', 'expensive', 'cheap', 'money', 'buy', 'purchase'],
            'shipping': ['ship', 'delivery', 'arrive', 'deliver', 'mail', 'time', 'when'],
            'description': ['about', 'description', 'detail', 'tell', 'what', 'summary', 'synopsis', 'yes'],
            'availability': ['available', 'stock', 'inventory', 'have', 'get', 'find'],
            'formats': ['format', 'kindle', 'ebook', 'pdf', 'epub', 'hardcover', 'paperback'],
            'author': ['author', 'writer', 'written', 'by who', 'who wrote'],
            'genre': ['genre', 'type', 'category', 'subject', 'kind of book'],
            'recommendation': ['recommend', 'suggest', 'similar', 'like', 'best', 'top'],
            'rating': ['rating', 'review', 'score', 'stars', 'popular']
        }

        self.intent_keywords.update({
            'identity': ['who are you', 'who r u', 'what are you', 'your name'],
            'capabilities': ['what can you do', 'help', 'features', 'abilities', 'looking', 'look', 'for'],
            'creator': ['who made you', 'who created you', 'developer'],
            'goodbye': ['bye', 'goodbye', 'see you', 'exit']
        })

        
        
        self.greeting_patterns = [
            r'hello', r'hi', r'hey', r'greetings', r'good morning', r'good afternoon'
        ]
        
        self.thanks_patterns = [
            r'thank', r'thanks', r'appreciate', r'grateful'
        ]

    def preprocess_text(self, text: str) -> List[str]:
        """Preprocess and tokenize input text"""
        text = text.lower()
        tokens = word_tokenize(text)
        # Remove stopwords and lemmatize
        tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words]
        return tokens

    def extract_book_from_query(self, query: str) -> Optional[Book]:
        """Extract book information from user query using database search"""
        db = get_db()
        
        # Try exact title match first
        words = query.split()
        possible_titles = []
        
        # Look for quoted titles
        quoted_titles = re.findall(r'"([^"]*)"', query)
        for title in quoted_titles:
            cursor = db.execute(
                "SELECT * FROM books WHERE LOWER(title) LIKE ? LIMIT 1",
                (f"%{title.lower()}%",)
            )
            row = cursor.fetchone()
            if row:
                return Book.from_row(row)
        
        # Try to find book by keywords in title
        tokens = self.preprocess_text(query)
        
        # Search for books with any of the tokens in title
        for i in range(len(tokens), 0, -1):
            for j in range(len(tokens) - i + 1):
                possible_title = " ".join(tokens[j:j+i])
                if len(possible_title) > 2:  # Avoid very short matches
                    cursor = db.execute(
                        "SELECT * FROM books WHERE LOWER(title) LIKE ? LIMIT 1",
                        (f"%{possible_title}%",)
                    )
                    row = cursor.fetchone()
                    if row:
                        return Book.from_row(row)
        
        # Search by author if no title found
        for token in tokens:
            cursor = db.execute(
                "SELECT * FROM books WHERE authors LIKE ? LIMIT 1",
                (f'%{token}%',)
            )
            row = cursor.fetchone()
            if row:
                return Book.from_row(row)
        
        # Search by subject/genre
        for token in tokens:
            cursor = db.execute(
                "SELECT * FROM books WHERE subjects LIKE ? LIMIT 1",
                (f'%{token}%',)
            )
            row = cursor.fetchone()
            if row:
                return Book.from_row(row)
        
        return None

    def detect_intent(self, tokens: List[str], raw_text: str = "") -> List[str]:
        detected = []

        joined = " ".join(tokens)

        for intent, keywords in self.intent_keywords.items():
            for kw in keywords:
                if kw in raw_text or kw in joined:
                    detected.append(intent)
                    break

        return detected if detected else ['general']


    def generate_price_response(self, book: Book) -> str:
        """Generate response for price inquiries"""
        if book.price > 0:
            return f"The price of '{book.title}' is ${book.price:.2f}."
        else:
            similar_books = self.get_similar_books(book, limit=3)
            if similar_books:
                avg_price = sum(b.price for b in similar_books if b.price > 0) / len(similar_books)
                return f"Exact price not available, but similar books average ${avg_price:.2f}."
            return f"Price information for '{book.title}' is not currently available."

    def generate_shipping_response(self, book: Book) -> str:
        """Generate response for shipping inquiries"""
        shipping_time = book.calculate_shipping_time()
        if book.stock > 0:
            return f"'{book.title}' will be delivered in {shipping_time}."
        else:
            return f"'{book.title}' is {shipping_time}. Would you like to be notified when it's back in stock?"

    def generate_description_response(self, book: Book) -> str:
        """Generate response for book description"""
        if book.summary:
            # Summarize if too long
            if len(book.summary) > 300:
                sentences = sent_tokenize(book.summary)
                summary = ' '.join(sentences[:2]) + "..."
                return f"About '{book.title}': {summary}"
            return f"About '{book.title}': {book.summary}"
        else:
            similar_books = self.get_similar_books(book, limit=1)
            if similar_books:
                return f"No description available. It's similar to '{similar_books[0].title}' which is about {similar_books[0].summary[:100]}..."
            return f"'{book.title}' is written by {book.authors[0]['name']} and falls under {', '.join(book.subjects[:3])}."

    def generate_availability_response(self, book: Book) -> str:
        """Generate response for availability inquiries"""
        if book.stock > 0:
            return f"'{book.title}' is available with {book.stock} copies in stock."
        else:
            return f"'{book.title}' is currently out of stock."

    def generate_formats_response(self, book: Book) -> str:
        """Generate response for format inquiries"""
        formats = book.get_formats_available()
        if formats:
            return f"'{book.title}' is available in: {', '.join(formats)}"
        else:
            return f"No specific format information available for '{book.title}'."

    def generate_recommendation_response(self, book: Optional[Book] = None) -> str:
        """Generate book recommendations"""
        db = get_db()
        
        if book:
            # Get similar books
            similar_books = self.get_similar_books(book, limit=3)
            if similar_books:
                titles = [b.title for b in similar_books]
                return f"If you like '{book.title}', you might also enjoy: {', '.join(titles)}"
        
        # Get top rated books
        cursor = db.execute(
            "SELECT * FROM books WHERE rating > 4.0 ORDER BY rating DESC LIMIT 3"
        )
        rows = cursor.fetchall()
        if rows:
            top_books = [Book.from_row(row) for row in rows]
            titles = [b.title for b in top_books]
            return f"Our top-rated books are: {', '.join(titles)}"
        
        return "I recommend checking out our bestsellers section on the website."

    def get_similar_books(self, book: Book, limit: int = 3) -> List[Book]:
        """Find books similar to the given book"""
        db = get_db()
        similar_books = []
        
        # Try to find by same subjects
        for subject in book.subjects:
            cursor = db.execute(
                "SELECT * FROM books WHERE subjects LIKE ? AND id != ? LIMIT ?",
                (f'%{subject}%', book.id, limit)
            )
            rows = cursor.fetchall()
            for row in rows:
                similar_book = Book.from_row(row)
                if similar_book not in similar_books:
                    similar_books.append(similar_book)
                    if len(similar_books) >= limit:
                        return similar_books
        
        # Try to find by same author
        for author in book.authors:
            cursor = db.execute(
                "SELECT * FROM books WHERE authors LIKE ? AND id != ? LIMIT ?",
                (f'%{author}%', book.id, limit)
            )
            rows = cursor.fetchall()
            for row in rows:
                similar_book = Book.from_row(row)
                if similar_book not in similar_books:
                    similar_books.append(similar_book)
                    if len(similar_books) >= limit:
                        return similar_books
        
        return similar_books

    def generate_response(self, user_input: str) -> str:
        """Main chatbot response generator"""
        user_input = user_input.lower().strip()
        
        # Check for greetings
        for pattern in self.greeting_patterns:
            if re.search(pattern, user_input):
                return "Hello! I'm your book assistant. How can I help you today?"
        
        # Check for thanks
        for pattern in self.thanks_patterns:
            if re.search(pattern, user_input):
                return "You're welcome! Is there anything else I can help you with?"
        
        # Extract book from query
        book = self.extract_book_from_query(user_input)
        if book:
            session['last_book_id'] = book.id
        # Preprocess and detect intents
        tokens = self.preprocess_text(user_input)
        intents = self.detect_intent(tokens)
        if 'last_book_id' in session:
            book = Book.get_by_id(int(session['last_book_id']))
        if not book:
            # No book found - offer general help
            if 'recommend' in user_input or 'suggest' in user_input:
                return self.generate_recommendation_response()
            elif 'help' in user_input:
                return "I can help you with: finding books, prices, descriptions, shipping info, and recommendations. Try asking about a specific book!"
            else:
                for intent in intents:
                    return self.capabilities_response()
                return "I couldn't find that book in our collection. Could you please specify the title, author, or genre?"
        
        # Generate responses for each detected intent
        responses = []
        
        for intent in intents:
            if intent == 'price':
                responses.append(self.generate_price_response(book))
            elif intent == 'shipping':
                responses.append(self.generate_shipping_response(book))
            elif intent == 'description':
                responses.append(self.generate_description_response(book))
            elif intent == 'availability':
                responses.append(self.generate_availability_response(book))
            elif intent == 'formats':
                responses.append(self.generate_formats_response(book))
            elif intent == 'author':
                responses.append(f"'{book.title}' is written by {book.authors[0]['name']}.")
            elif intent == 'genre':
                responses.append(f"'{book.title}' falls under: {', '.join(book.subjects[:3])}.")
            elif intent == 'identity':
                responses.append(self.identity_response())
            elif intent == 'capabilities':
                responses.append(self.capabilities_response())
            elif intent == 'creator':
                responses.append(self.creator_response())
            elif intent == 'goodbye':
                responses.append(self.goodbye_response())
            elif intent == 'rating':
                if book.rating > 0:
                    responses.append(f"'{book.title}' has a rating of {book.rating}/5.")
                else:
                    responses.append(f"No ratings available for '{book.title}' yet.")
            elif intent == 'recommendation':
                responses.append(self.generate_recommendation_response(book))
            elif intent == 'general':
                # General book info
                
                responses.append(f"I found '{book.title}' by {book.authors[0]['name']}. What would you like to know about it?")
        
        # Combine responses
        if len(responses) == 1:
            return responses[0]
        else:
            return "Here's what I found:\n" + "\n".join(f"• {response}" for response in responses)
        
    def identity_response(self):
        return "I’m a virtual book assistant. I help you find books, prices, descriptions, and recommendations."

    def capabilities_response(self):
        return (
            "I can help you with:\n"
            "• Book prices\n"
            "• Descriptions & summaries\n"
            "• Availability & formats\n"
            "• Recommendations\n"
            "Just ask about a book!"
        )

    def creator_response(self):
        return "I was created by the development team to help users explore books easily."

    def goodbye_response(self):
        session.pop('last_book_id', None)
        return "Goodbye! 📚 Feel free to come back anytime."



