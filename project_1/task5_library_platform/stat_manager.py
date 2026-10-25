"""聚合统计：分类、年度趋势、热门图书、读者与学院统计。"""
def category_stats(db):
    return list(db.books.aggregate([
        {"$group": {
            "_id": "$category",
            "book_count": {"$sum": 1},
            "total_stock": {"$sum": "$stock"},
            "avg_price_raw": {"$avg": "$price"}
        }},
        {"$project": {"book_count": 1, "total_stock": 1,
                       "avg_price": {"$round": ["$avg_price_raw", 2]}}},
        {"$sort": {"total_stock": -1, "_id": 1}}
    ]))

def yearly_trend(db):
    # 用不会因时间序列 TTL 丢失旧数据的 archive 作统计。
    return list(db.borrow_archive.aggregate([
        {"$group": {"_id": {"$year": {"date": "$borrow_date",
                                      "timezone": "Asia/Shanghai"}},
                    "borrow_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "year": {"$concat": [
            {"$toString": "$_id"}, "年"]}, "borrow_count": 1}}
    ]))

def popular_books(db, limit=5):
    return list(db.books.aggregate([
        {"$sort": {"borrow_count": -1, "isbn": 1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "isbn": 1, "title": 1,
                       "category": 1, "borrow_count": 1}}
    ]))

def active_readers(db, limit=5):
    return list(db.borrow_archive.aggregate([
        {"$group": {"_id": "$reader_card", "borrow_count": {"$sum": 1}}},
        {"$sort": {"borrow_count": -1, "_id": 1}},
        {"$limit": limit},
        {"$lookup": {"from": "readers", "localField": "_id",
                     "foreignField": "card_no", "as": "reader"}},
        {"$unwind": {"path": "$reader", "preserveNullAndEmptyArrays": True}},
        {"$project": {"card_no": "$_id", "name": "$reader.name",
                       "borrow_count": 1, "_id": 0}}
    ]))

def save_category_stats(db):
    pipe = [
        {"$group": {
            "_id": "$category", "book_count": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"},
            "min_stock": {"$min": "$stock"},
            "max_stock": {"$max": "$stock"}
        }},
        {"$merge": {
            "into": "category_stats", "on": "_id",
            "whenMatched": "replace", "whenNotMatched": "insert"
        }}
    ]
    list(db.books.aggregate(pipe))
    return db.category_stats.count_documents({})
