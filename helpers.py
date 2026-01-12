import json
import os
from models.book import Book
import random

def get_books_from_json()->list[Book]:
    with open("books.json", "r") as f:
        books = json.loads(f.read())
    book_models: list[Book] = []
    for book in books:
        book_models.append(Book.toBook(book))
    return book_models

def search_book_by_id(book_id: int):
    print(book_id)
    for index, book in enumerate(get_books_from_json()):
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

def generate_random_price_and_stock(price_range: set, stock_range: set) -> dict:
    price = random.randint(price_range[0], price_range[1])
    stock = random.randint(stock_range[0], stock_range[1])

    return {
        "price": price,
        "stock": stock
    }