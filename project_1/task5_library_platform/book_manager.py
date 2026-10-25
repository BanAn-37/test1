"""图书管理：增删改查、组合检索、排行榜。"""
import re
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError

def search_books(db, keyword="", category="", min_price=None, max_price=None,
                 available_only=False, limit=100):
    conditions = []
    if keyword:
        rx = re.escape(keyword)
        conditions.append({"$or": [
            {"title": {"$regex": rx, "$options": "i"}},
            {"author": {"$regex": rx, "$options": "i"}},
            {"isbn": {"$regex": rx}}
        ]})
    if category:
        conditions.append({"category": category})
    price = {}
    if min_price is not None:
        price["$gte"] = min_price
    if max_price is not None:
        price["$lte"] = max_price
    if price:
        conditions.append({"price": price})
    if available_only:
        conditions.append({"stock": {"$gt": 0}})
    query = {"$and": conditions} if conditions else {}
    return list(db.books.find(query).sort("title", 1).limit(limit))

def find_by_isbn(db, isbn):
    return db.books.find_one({"isbn": isbn})

def add_book(db, book):
    book = dict(book)
    book.setdefault("borrow_count", 0)
    book.setdefault("tags", [])
    book.setdefault("publish_date", datetime.now(timezone.utc))
    if book["stock"] < 0 or not (0 <= book["rating"] <= 5):
        raise ValueError("库存必须非负，评分必须在 0～5 之间")
    return db.books.insert_one(book).inserted_id

def add_many_books(db, books):
    docs = list(books)
    return len(db.books.insert_many(docs).inserted_ids) if docs else 0

def update_stock(db, isbn, new_stock):
    if new_stock < 0:
        raise ValueError("库存不能小于 0")
    return db.books.update_one(
        {"isbn": isbn}, {"$set": {"stock": new_stock},
                         "$currentDate": {"updated_at": True}}
    ).modified_count

def delete_book(db, isbn):
    active = db.borrow_archive.count_documents({
        "book_isbn": isbn,
        "return_date": {"$exists": False},
        "status": {"$in": ["借出", "逾期"]}
    })
    if active:
        raise ValueError("存在尚未归还的借阅记录，不能删除该图书")
    return db.books.delete_one({"isbn": isbn}).deleted_count

def delete_zero_stock_books(db):
    """只删除无库存且没有未归还借阅的图书；调用前必须让用户确认。"""
    blocked = db.borrow_archive.distinct("book_isbn", {
        "status": {"$in": ["借出", "逾期"]},
        "return_date": {"$exists": False}
    })
    return db.books.delete_many({"stock": 0, "isbn": {"$nin": blocked}}).deleted_count

def top_rated(db, limit=5):
    return list(db.books.find(
        {}, {"_id": 0, "isbn": 1, "title": 1, "rating": 1, "borrow_count": 1}
    ).sort("rating", -1).limit(limit))
