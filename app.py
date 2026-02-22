from flask import Flask, render_template, jsonify, request, session
from helpers import get_books_from_json, generate_random_rating,generate_random_price_and_stock
from models.book import Book
from flask_socketio import SocketIO, emit
from bot.bot import BookChatbot
from datetime import datetime, timedelta
from db import init_db, get_db

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SESSION_PERMANENT'] = True
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
            book.rating = generate_random_rating()
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

# @app.route("/support")
# def support():
#     template_data = {
#         "title": "Chat Support",
#     }
#     return render_template("support.html", template_data=template_data)

@app.route("/book/<int:id>/view")
def view(id: int):
    book = Book.get_by_id(id)
    template_data = {
        "title": book.title,
        # "book": book
    }
    return render_template("book_view.html", template_data = template_data, book = book)
@socket.on("connect", namespace="/bot")
def handle_connect():
    """Handle client connection"""
    print(f"Client connected to bot. Session ID: {request.sid}")
    
    if 'chat_history' in session and len(session['chat_history']) > 0:
        emit("chat_init", {
            "response": "Welcome back! How can I help you with books today? 📚",
            "history": chatbot.get_chat_history()
        })
    else:
        emit("chat_init", {
            "response": chatbot.capabilities_response(),
            "history": []
        })

@socket.on("disconnect", namespace="/bot")
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected from bot. Session ID: {request.sid}")

@socket.on("chat_open", namespace="/bot")
def chat_open():
    """Handle chat open event"""
    print("Chat opened")
    history = chatbot.get_chat_history()
    if history:
        recent = history[-4:] 
        emit("chat_init", {
            "response": "Continuing our conversation...",
            "history": recent
        })
    else:
        emit("chat_init", {
            "response": chatbot.capabilities_response(),
            "history": []
        })

@socket.on("message", namespace="/bot")
def handle_message(data):
    """
    Handle incoming messages
    data example:
    {
        "message": "Tell me about Frankenstein"
    }
    """
    if not data or "message" not in data:
        emit("message", {
            "response": "Invalid message format.",
            "timestamp": datetime.now().isoformat()
        })
        return
    
    user_input = data["message"].strip()
    if not user_input:
        emit("message", {
            "response": "Please type a message.",
            "timestamp": datetime.now().isoformat()
        })
        return

    emit("message", {
        "is_typing": True,
        "timestamp": datetime.now().isoformat()
    })
    
    bot_response = chatbot.generate_response(user_input)

    emit("message", {
        "response": bot_response,
        "timestamp": datetime.now().isoformat()
    })

@socket.on("clear_history", namespace="/bot")
def clear_history():
    """Clear conversation history"""
    chatbot.clear_history()
    emit("chat_init", {
        "response": "Conversation history cleared. How can I help you?",
        "history": []
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