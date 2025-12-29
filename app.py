from flask import Flask, render_template, jsonify
from BookAPI import BookAPI
import json
import os

app = Flask(__name__)
books = []
cache_search = {} 
if(len(books) <= 0):
    with open("books.json", "r") as f:
        books = json.loads(f.read())

def search_book_by_id(book_id: int):
    print(book_id)
    for index, book in enumerate(books):
        print(book.get("title"))
        if book.get("id") == book_id:
            return index
    return -1


def cache_search_or_save(book_id: int):
    cache_file = "cache_search.json"
    key = str(book_id)

    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            try:
                temp = json.load(f)
            except json.JSONDecodeError:
                temp = {}
    else:
        temp = {}
    if key in temp:
        return temp[key]
    result = search_book_by_id(book_id)
    temp[key] = result
    with open(cache_file, "w") as f:
        json.dump(temp, f)
    return result

@app.route("/")
def index():
    global books
    template_data = {
        "title": "Home",
        "books": books
    }
    return render_template("index.html", template_data = template_data) 

@app.route("/book/<int:id>/view")
def view(id: int):
    global books
    book = books[cache_search_or_save(id)]
    template_data = {
        "title": book.get('title'),
        # "book": book
    }
    return render_template("book_view.html", template_data = template_data, book = book)