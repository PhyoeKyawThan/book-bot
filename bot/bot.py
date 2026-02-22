import nltk
import re
import random
import json
import time
from typing import List, Dict, Optional, Tuple
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from db import get_db
from models.book import Book
from nltk.stem import WordNetLemmatizer
from flask import session

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

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

class BookChatbot:
    def __init__(self):
        self.intent_keywords = {
            'price': ['price', 'cost', 'worth', 'expensive', 'cheap', 'money', 'buy', 'purchase', 'how much', 'pay'],
            'shipping': ['ship', 'delivery', 'arrive', 'deliver', 'mail', 'time', 'when', 'shipping', 'get here', 'arrival'],
            'description': ['about', 'description', 'detail', 'tell', 'what', 'summary', 'synopsis', 'yes', 'describe', 'explain'],
            'availability': ['available', 'stock', 'inventory', 'have', 'get', 'find', 'in stock', 'out of stock', 'copies'],
            'formats': ['format', 'kindle', 'ebook', 'pdf', 'epub', 'hardcover', 'paperback', 'audiobook', 'digital', 'physical'],
            'author': ['author', 'writer', 'written', 'by who', 'who wrote', 'authored', 'created by'],
            'genre': ['genre', 'type', 'category', 'subject', 'kind of book', 'what kind', 'category'],
            'recommendation': ['recommend', 'suggest', 'similar', 'like', 'best', 'top', 'favorite', 'similar to', 'any good'],
            'rating': ['rating', 'review', 'score', 'stars', 'popular', 'rate', 'rated', 'good read', 'worth reading']
        }

        self.intent_keywords.update({
            'identity': ['who are you', 'who r u', 'what are you', 'your name', 'introduce yourself'],
            'capabilities': ['what can you do', 'help', 'features', 'abilities', 'looking', 'look', 'for', 'can you', 'function'],
            'creator': ['who made you', 'who created you', 'developer', 'built you', 'your creator'],
            'goodbye': ['bye', 'goodbye', 'see you', 'exit', 'quit', 'talk later'],
            'greeting': ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening'],
            'thanks': ['thank', 'thanks', 'appreciate', 'grateful', 'helpful']
        })
        
        self.greeting_responses = [
            "Hello there! I'm your book-loving assistant. How can I help you today? 📚",
            "Hi! Ready to dive into the world of books? What are you looking for?",
            "Hey! I'm here to help you find your next great read. What brings you here?",
            "Greetings, book lover! How can I assist you today?",
            "Hello! Whether you need book info or recommendations, I'm here to help!"
        ]
        
        self.thanks_responses = [
            "You're very welcome! Happy reading! 📖",
            "Glad I could help! Is there anything else you'd like to know?",
            "My pleasure! Don't hesitate to ask if you need more book recommendations.",
            "Anytime! That's what I'm here for.",
            "You're welcome! Enjoy your book! 📚"
        ]
        
        self.goodbye_responses = [
            "Goodbye! Come back anytime for more book recommendations! 📚",
            "See you later, book lover! Happy reading!",
            "Take care! I'll be here when you need book help again.",
            "Bye! Hope you find your next favorite book!",
            "Until next time! Keep turning those pages! 📖"
        ]
        
        self.fallback_responses = [
            "I'm not quite sure I understood. Could you rephrase that?",
            "Hmm, I'm still learning. Can you ask about books in a different way?",
            "I'm not sure I caught that. You can ask me about book prices, descriptions, or recommendations!",
            "Sorry, I didn't quite get that. Try asking about a specific book or author.",
            "I'm here to help with books! Ask me about titles, authors, prices, or get recommendations."
        ]
        
        self.no_book_found_responses = [
            "I couldn't find that book in our collection. Could you check the title or author?",
            "Hmm, that book doesn't seem to be in our database. Want to try a different title?",
            "Sorry, I don't recognize that book. Could you provide more details?",
            "I searched but couldn't find that one. Maybe try searching by author or genre?",
            "That book isn't in our system yet. Would you like a recommendation instead?"
        ]
        
        self.capability_details = {
            'price': "I can tell you how much books cost and if they're on sale.",
            'shipping': "I can give you delivery time estimates and shipping options.",
            'description': "I can tell you what books are about and provide summaries.",
            'availability': "I can check if books are in stock and how many copies we have.",
            'formats': "I can tell you what formats books come in (ebook, paperback, etc.).",
            'author': "I can give you information about authors and their works.",
            'genre': "I can help you find books by genre or category.",
            'recommendation': "I can suggest books based on your interests.",
            'rating': "I can tell you how other readers have rated books."
        }

    def get_session_history(self) -> List[Dict]:
        """Retrieve conversation history from session"""
        if 'chat_history' not in session:
            session['chat_history'] = []
        return session['chat_history']

    def add_to_history(self, role: str, message: str):
        """Add a message to conversation history"""
        history = self.get_session_history()
        history.append({
            'role': role,
            'message': message,
            'timestamp': time.time()
        })
        if len(history) > 20:
            history = history[-20:]
        session['chat_history'] = history
        session.modified = True

    def get_context(self) -> str:
        """Get conversation context from history"""
        history = self.get_session_history()
        if len(history) < 2:
            return ""
        
        recent = history[-6:] if len(history) > 6 else history
        context = []
        for entry in recent:
            role = "User" if entry['role'] == 'user' else "Bot"
            context.append(f"{role}: {entry['message']}")
        
        return "\n".join(context[-3:]) 

    def preprocess_text(self, text: str) -> List[str]:
        text = text.lower()
        tokens = word_tokenize(text)
        tokens = [lemmatizer.lemmatize(token) for token in tokens if token.isalnum() and token not in stop_words]
        return tokens

    def extract_book_from_query(self, query: str) -> Optional[Book]:
        db = get_db()
        
        quoted_titles = re.findall(r'"([^"]*)"', query)
        for title in quoted_titles:
            cursor = db.execute(
                "SELECT * FROM books WHERE LOWER(title) LIKE ? LIMIT 1",
                (f"%{title.lower()}%",)
            )
            row = cursor.fetchone()
            if row:
                return Book.from_row(row)
        
        tokens = self.preprocess_text(query)
        
        for i in range(min(len(tokens), 4), 0, -1):
            for j in range(len(tokens) - i + 1):
                possible_title = " ".join(tokens[j:j+i])
                if len(possible_title) > 3:
                    cursor = db.execute(
                        "SELECT * FROM books WHERE LOWER(title) LIKE ? LIMIT 1",
                        (f"%{possible_title}%",)
                    )
                    row = cursor.fetchone()
                    if row:
                        return Book.from_row(row)
        
        for token in tokens:
            cursor = db.execute(
                "SELECT * FROM books WHERE LOWER(authors) LIKE ? LIMIT 1",
                (f'%{token}%',)
            )
            row = cursor.fetchone()
            if row:
                return Book.from_row(row)
        
        for token in tokens:
            cursor = db.execute(
                "SELECT * FROM books WHERE LOWER(subjects) LIKE ? LIMIT 1",
                (f'%{token}%',)
            )
            row = cursor.fetchone()
            if row:
                return Book.from_row(row)
        
        return None

    def detect_intent(self, tokens: List[str], raw_text: str = "") -> List[str]:
        detected = []
        joined = " ".join(tokens)
        raw_lower = raw_text.lower()

        context = self.get_context()
        if "what about" in raw_lower and "last_book_id" in session:
            detected.append('description')
        
        for intent, keywords in self.intent_keywords.items():
            for kw in keywords:
                if kw in raw_lower or kw in joined:
                    detected.append(intent)
                    break
                elif ' ' not in kw and re.search(r'\b' + re.escape(kw) + r'\b', raw_lower):
                    detected.append(intent)
                    break

        seen = set()
        unique_detected = []
        for intent in detected:
            if intent not in seen:
                seen.add(intent)
                unique_detected.append(intent)
        
        return unique_detected if unique_detected else ['general']

    def generate_price_response(self, book: Book) -> str:
        if book.price > 0:
            responses = [
                f"The price of '{book.title}' is ${book.price:.2f}. Great choice!",
                f"'{book.title}' costs ${book.price:.2f}. Would you like to know more about it?",
                f"You can get '{book.title}' for ${book.price:.2f}. That's a fantastic read!",
                f"It's ${book.price:.2f} for '{book.title}'. Interested in purchasing it?"
            ]
            return random.choice(responses)
        else:
            similar_books = self.get_similar_books(book, limit=3)
            if similar_books:
                avg_price = sum(b.price for b in similar_books if b.price > 0) / len(similar_books)
                responses = [
                    f"I don't have the exact price for '{book.title}', but similar books average around ${avg_price:.2f}.",
                    f"Price info isn't available for this one, but books like it typically cost about ${avg_price:.2f}.",
                    f"While I can't find the exact price, similar titles are usually priced around ${avg_price:.2f}."
                ]
                return random.choice(responses)
            return f"Sorry, I don't have price information for '{book.title}' at the moment."

    def generate_shipping_response(self, book: Book) -> str:
        shipping_time = book.calculate_shipping_time()
        if book.stock > 0:
            responses = [
                f"Good news! '{book.title}' will be delivered in {shipping_time}.",
                f"You can expect '{book.title}' to arrive in {shipping_time} after ordering.",
                f"Shipping takes about {shipping_time} for '{book.title}'. It's in stock and ready to go!"
            ]
            return random.choice(responses)
        else:
            responses = [
                f"'{book.title}' is {shipping_time}. Would you like me to notify you when it's back?",
                f"Unfortunately, '{book.title}' is {shipping_time}. Want me to suggest similar books?",
                f"This book is {shipping_time}. I can recommend some great alternatives if you'd like!"
            ]
            return random.choice(responses)

    def generate_description_response(self, book: Book) -> str:
        if book.summary:
            if len(book.summary) > 300:
                sentences = sent_tokenize(book.summary)
                summary = ' '.join(sentences[:2]) + "..."
                responses = [
                    f"Here's what '{book.title}' is about: {summary}",
                    f"Let me tell you about '{book.title}': {summary}",
                    f"'{book.title}' tells the story of {summary}"
                ]
                return random.choice(responses)
            else:
                responses = [
                    f"About '{book.title}': {book.summary}",
                    f"Here's the description: {book.summary}",
                    f"'{book.title}' is described as: {book.summary}"
                ]
                return random.choice(responses)
        else:
            similar_books = self.get_similar_books(book, limit=1)
            if similar_books:
                return f"I don't have a description for '{book.title}', but it's similar to '{similar_books[0].title}' which is about {similar_books[0].summary[:150]}..."
            return f"'{book.title}' is written by {book.authors[0]['name']} and fits in the {', '.join(book.subjects[:2])} genre."

    def generate_availability_response(self, book: Book) -> str:
        if book.stock > 0:
            responses = [
                f"Yes! '{book.title}' is in stock with {book.stock} copies available.",
                f"Great news - we have {book.stock} copies of '{book.title}' ready to ship!",
                f"'{book.title}' is available right now with {book.stock} copies in our inventory."
            ]
            return random.choice(responses)
        else:
            responses = [
                f"I'm sorry, '{book.title}' is currently out of stock. Would you like me to suggest something similar?",
                f"'{book.title}' isn't available right now. I can recommend some other great books if you're interested!",
                f"This book is temporarily out of stock. Want to check out some similar titles instead?"
            ]
            return random.choice(responses)

    def generate_formats_response(self, book: Book) -> str:
        formats = book.get_formats_available()
        if formats:
            format_list = ', '.join(formats[:-1]) + f" and {formats[-1]}" if len(formats) > 1 else formats[0]
            responses = [
                f"'{book.title}' comes in {format_list}. Which format would you prefer?",
                f"You can get '{book.title}' in {format_list}. Great options!",
                f"'{book.title}' is available as {format_list}. Take your pick!"
            ]
            return random.choice(responses)
        else:
            responses = [
                f"I don't have format details for '{book.title}' right now.",
                f"Sorry, I'm not sure what formats '{book.title}' comes in.",
                f"Format information for '{book.title}' isn't currently available."
            ]
            return random.choice(responses)

    def generate_recommendation_response(self, book: Optional[Book] = None) -> str:
        db = get_db()
        
        if book:
            similar_books = self.get_similar_books(book, limit=3)
            if similar_books:
                titles = [f"'{b.title}'" for b in similar_books]
                book_list = ', '.join(titles[:-1]) + f" and {titles[-1]}" if len(titles) > 1 else titles[0]
                responses = [
                    f"Since you like '{book.title}', you might also enjoy {book_list}!",
                    f"Readers who enjoyed '{book.title}' also loved {book_list}.",
                    f"If you're a fan of '{book.title}', I think you'd really like {book_list}!"
                ]
                return random.choice(responses)
        
        cursor = db.execute(
            "SELECT * FROM books WHERE rating > 4.0 ORDER BY rating DESC LIMIT 3"
        )
        rows = cursor.fetchall()
        if rows:
            top_books = [Book.from_row(row) for row in rows]
            titles = [f"'{b.title}'" for b in top_books]
            book_list = ', '.join(titles[:-1]) + f" and {titles[-1]}" if len(titles) > 1 else titles[0]
            responses = [
                f"Here are some highly-rated books you might enjoy: {book_list}!",
                f"Based on reader reviews, I'd recommend {book_list}.",
                f"Some of our most popular books right now are {book_list}. Worth checking out!"
            ]
            return random.choice(responses)
        
        return "I'd recommend browsing our bestsellers section - there are so many great books to discover!"

    def get_similar_books(self, book: Book, limit: int = 3) -> List[Book]:
        db = get_db()
        similar_books = []
        seen_ids = {book.id}
        
        for subject in book.subjects[:3]:
            cursor = db.execute(
                "SELECT * FROM books WHERE subjects LIKE ? AND id != ? LIMIT ?",
                (f'%{subject}%', book.id, limit)
            )
            rows = cursor.fetchall()
            for row in rows:
                similar_book = Book.from_row(row)
                if similar_book.id not in seen_ids:
                    seen_ids.add(similar_book.id)
                    similar_books.append(similar_book)
                    if len(similar_books) >= limit:
                        return similar_books
        
        if len(similar_books) < limit:
            for author in book.authors[:2]:
                cursor = db.execute(
                    "SELECT * FROM books WHERE authors LIKE ? AND id != ? LIMIT ?",
                    (f'%{author["name"]}%', book.id, limit - len(similar_books))
                )
                rows = cursor.fetchall()
                for row in rows:
                    similar_book = Book.from_row(row)
                    if similar_book.id not in seen_ids:
                        seen_ids.add(similar_book.id)
                        similar_books.append(similar_book)
                        if len(similar_books) >= limit:
                            return similar_books
        
        return similar_books

    def handle_general_conversation(self, user_input: str) -> Optional[str]:
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            return random.choice(self.greeting_responses)
        
        if any(word in user_input_lower for word in ['thank', 'thanks', 'appreciate']):
            return random.choice(self.thanks_responses)
        
        if any(word in user_input_lower for word in ['bye', 'goodbye', 'exit', 'quit', 'see you']):
            session.pop('chat_history', None)
            session.pop('last_book_id', None)
            return random.choice(self.goodbye_responses)
        
        if any(phrase in user_input_lower for phrase in ['who are you', 'what are you', 'your name']):
            return "I'm BookBuddy, your personal book assistant! I'm here to help you discover great reads and answer questions about our book collection. 📚"
        
        if any(word in user_input_lower for word in ['help', 'what can you do', 'capabilities', 'features']):
            capabilities = "\n".join([f"• {cap}: {desc}" for cap, desc in self.capability_details.items()])
            return f"I can help you with lots of book-related things!\n\n{capabilities}\n\nJust ask me about any book or tell me what you're looking for!"
        
        if any(phrase in user_input_lower for phrase in ['who made you', 'who created you', 'your creator']):
            return "I was created by a team of book-loving developers to make discovering new books easier and more fun!"
        
        return None

    def generate_response(self, user_input: str) -> str:
        user_input = user_input.strip()
        
        self.add_to_history('user', user_input)
        
        general_response = self.handle_general_conversation(user_input)
        if general_response:
            self.add_to_history('bot', general_response)
            return general_response
        
        book = self.extract_book_from_query(user_input)
        if book:
            session['last_book_id'] = book.id
        
        if 'last_book_id' in session and not book:
            context = self.get_context()
            if any(word in user_input.lower() for word in ['it', 'this', 'that', 'the book']):
                book = Book.get_by_id(int(session['last_book_id']))
        
        tokens = self.preprocess_text(user_input)
        intents = self.detect_intent(tokens, user_input)
        
        if not book:
            if any(intent in ['recommendation', 'general'] for intent in intents):
                response = self.generate_recommendation_response()
            elif any(intent in ['capabilities', 'help'] for intent in intents):
                response = self.capabilities_response()
            else:
                responses = [
                    f"I couldn't find that book. Did you mean one of these? {self.suggest_books_from_query(user_input)}",
                    random.choice(self.no_book_found_responses)
                ]
                response = random.choice(responses)
            
            self.add_to_history('bot', response)
            return response
        
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
                author_name = book.authors[0]['name'] if book.authors else "an unknown author"
                responses.append(f"'{book.title}' was written by {author_name}.")
            elif intent == 'genre':
                genres = ', '.join(book.subjects[:3])
                responses.append(f"'{book.title}' falls under: {genres}.")
            elif intent == 'rating':
                if book.rating and book.rating > 0:
                    responses.append(f"'{book.title}' has a rating of {book.rating}/5 from readers.")
                else:
                    responses.append(f"'{book.title}' doesn't have any ratings yet. Be the first to review it!")
            elif intent == 'recommendation':
                responses.append(self.generate_recommendation_response(book))
        
        if not responses:
            responses.append(f"I found '{book.title}' by {book.authors[0]['name'] if book.authors else 'unknown author'}. What would you like to know about it? I can tell you about the price, description, availability, and more!")
        
        if len(responses) == 1:
            final_response = responses[0]
        else:
            final_response = " ".join(responses)
            if random.random() > 0.5:
                final_response += " " + random.choice([
                    "Is there anything else you'd like to know about this book?",
                    "Can I help you with anything else?",
                    "Would you like more details about anything specific?"
                ])
        
        self.add_to_history('bot', final_response)
        return final_response

    def suggest_books_from_query(self, query: str) -> str:
        db = get_db()
        tokens = self.preprocess_text(query)
        
        suggestions = []
        for token in tokens[:3]:
            cursor = db.execute(
                "SELECT title FROM books WHERE LOWER(title) LIKE ? LIMIT 2",
                (f'%{token}%',)
            )
            rows = cursor.fetchall()
            for row in rows:
                if row['title'] not in suggestions:
                    suggestions.append(row['title'])
                    if len(suggestions) >= 3:
                        break
            if len(suggestions) >= 3:
                break
        
        if suggestions:
            return ', '.join([f"'{s}'" for s in suggestions])
        return "Try searching by title or author name"

    def capabilities_response(self) -> str:
        return (
            "I can help you with all things books! 📚\n\n"
            "• Check prices and availability\n"
            "• Give you book descriptions and summaries\n"
            "• Tell you about authors and genres\n"
            "• Suggest books based on your interests\n"
            "• Provide shipping and format information\n\n"
            "Just ask me about any book you're interested in!"
        )