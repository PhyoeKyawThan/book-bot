from flask import Flask, render_template, jsonify, request
from helpers import get_books_from_json, generate_random_price_and_stock
from models.book import Book
from flask_socketio import SocketIO, emit
from bot import BookChatbot
from datetime import datetime
from db import init_db, get_db

app = Flask(__name__)
app.config['SECRET_KEY'] = "it'sasecret"
socket = SocketIO(app=app)
chatbot = BookChatbot()

def check_data_exists_or_insert_books() -> None:
    """Check if books table has data, if not insert from JSON"""
    db = get_db()
    
    cursor = db.execute("SELECT COUNT(*) as book_count FROM books")
    result = cursor.fetchone()
    if result and result['book_count'] == 0:
        print("No books found in database. Inserting sample data...")
        sample_books = get_books_from_json()
        
        for book in sample_books:
            random_price_stock = generate_random_price_and_stock((10000, 50000), (50, 100))
            book.price = random_price_stock.get('price')
            book.stock = random_price_stock.get('stock')
            print(random_price_stock)
            book_id = Book.create(book)
            print(f"Book '{book.title}' created with ID: {book_id}")
        
        print(f"Successfully inserted {len(sample_books)} books")
    else:
        print(f"Database already has {result['book_count']} books")


with app.app_context():
    init_db(check_data_exists_or_insert_books)

# routes
@app.route("/")
def index():
    books = Book.get_all()
    print(books)
    template_data = {
        "title": "Home",
        "books": books
    }
    return render_template("index.html", template_data = template_data) 

@app.route("/book/<int:id>/view")
def view(id: int):
    book = Book.get_by_id(id)
    template_data = {
        "title": book.title,
        # "book": book
    }
    return render_template("book_view.html", template_data = template_data, book = book)

@socket.on("message", namespace="/bot")
def handle_message(data):
    """
    data example:
    {
        "message": "Tell me about Frankenstein"
    }
    """
    if not data or "message" not in data:
        emit("message", {
            "response": "Invalid message format."
        })
        return
    emit("message", {
        "is_typing": True,
        "response": "Typing...",
        "timestamp": datetime.now().isoformat()
    })
    user_input = data["message"]
    bot_response = chatbot.generate_response(user_input)

    emit("message", {
        "response": bot_response,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json

    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    response = chatbot.generate_response(data['message'])

    return jsonify({
        'response': response,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/books/search', methods=['GET'])
def search_books():
    """Search books for chatbot context"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
    
    book = chatbot.extract_book_from_query(query)
    
    if book:
        return jsonify({
            'found': True,
            'book': book.to_dict(),
            'suggested_questions': [
                f"What's the price of {book.title}?",
                f"When will {book.title} be delivered?",
                f"Tell me about {book.title}",
                f"Is {book.title} available now?",
                f"What formats is {book.title} available in?"
            ]
        })
    else:
        # Suggest alternative books
        db = get_db()
        cursor = db.execute(
            "SELECT * FROM books WHERE title LIKE ? OR authors LIKE ? LIMIT 5",
            (f'%{query}%', f'%{query}%')
        )
        rows = cursor.fetchall()
        
        if rows:
            books = [Book.from_row(row).to_dict() for row in rows]
            return jsonify({
                'found': False,
                'suggestions': books,
                'message': f"Didn't find '{query}', but here are some similar books:"
            })
        else:
            return jsonify({
                'found': False,
                'message': "No books found. Try a different search term."
            })
