"""读者管理：信息检索、注册、学院与等级分布。"""
from datetime import datetime, timezone

def get_reader(db, card_no):
    return db.readers.find_one({"card_no": card_no})

def list_readers(db, college="", limit=100):
    query = {"college": college} if college else {}
    return list(db.readers.find(query).sort("card_no", 1).limit(limit))

def add_reader(db, card_no, name, college, email, phone, level, fav_categories=None):
    if db.readers.find_one({"card_no": card_no}, {"_id": 1}):
        raise ValueError("借阅证号已存在，不能重复注册")
    return db.readers.insert_one({
        "card_no": card_no,
        "name": name,
        "college": college,
        "email": email or None,
        "phone": phone,
        "level": level,
        "register_date": datetime.now(timezone.utc),
        "fav_categories": fav_categories or []
    }).inserted_id

def college_stats(db):
    return list(db.readers.aggregate([
        {"$group": {"_id": "$college", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}}
    ]))

def level_stats(db):
    return list(db.readers.aggregate([
        {"$group": {"_id": "$level", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]))

def college_count(db, college):
    return db.readers.count_documents({"college": college})

def all_colleges(db):
    return sorted(db.readers.distinct("college"))
