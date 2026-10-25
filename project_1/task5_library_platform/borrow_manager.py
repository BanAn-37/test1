"""借阅与归还。

borrow_archive 是可更新且不会因 TTL 丢失的历史记录/业务状态表；
borrow_logs 是任务书要求的时间序列集合，仅追加事件，不直接改 status。
"""
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from pymongo import ReturnDocument

LOAN_DAYS = 30

def register_borrow(db, card_no, isbn):
    if db.readers.find_one({"card_no": card_no}) is None:
        raise ValueError("借阅证号不存在")
    updated_book = db.books.find_one_and_update(
        {"isbn": isbn, "stock": {"$gt": 0}},
        {"$inc": {"stock": -1, "borrow_count": 1}},
        return_document=ReturnDocument.AFTER
    )
    if updated_book is None:
        raise ValueError("ISBN 不存在或库存不足")
    timestamp = datetime.now(timezone.utc)
    loan = {
        "borrow_date": timestamp,
        "reader_card": card_no,
        "book_isbn": isbn,
        "status": "借出"
    }
    try:
        inserted = db.borrow_archive.insert_one(loan)
    except Exception:
        db.books.update_one(
            {"isbn": isbn}, {"$inc": {"stock": 1, "borrow_count": -1}}
        )
        raise

    warning = []
    event = {
        "borrow_date": timestamp, "reader_card": card_no,
        "book_isbn": isbn, "status": "借出",
        "event_type": "借阅", "archive_id": str(inserted.inserted_id)
    }
    try:
        db.borrow_logs.insert_one(event)
    except Exception as exc:
        warning.append("时间序列事件写入失败；主借阅记录已成功：" + str(exc))
    try:
        db.book_logs.insert_one({"date": timestamp, "action": "borrow",
                                 "isbn": isbn, "reader_card": card_no})
    except Exception as exc:
        warning.append("审计日志写入失败：" + str(exc))
    return {"loan_id": str(inserted.inserted_id), "updated": 1,
            "stock": updated_book["stock"], "warnings": warning}

def list_loans(db, card_no="", limit=50):
    query = {"reader_card": card_no} if card_no else {}
    return list(db.borrow_archive.find(query).sort("borrow_date", -1).limit(limit))

def overdue_loans(db):
    # 根据当前日期与 30 天期限计算未还逾期，不依赖数据集中已归还的“逾期”标签。
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAN_DAYS)
    return list(db.borrow_archive.find({
        "borrow_date": {"$lt": cutoff},
        "return_date": {"$exists": False},
        "status": {"$in": ["借出", "逾期"]}
    }).sort("borrow_date", 1))

def return_book(db, loan_id):
    if not ObjectId.is_valid(loan_id):
        raise ValueError("借阅记录 ID 应为 24 位 ObjectId 字符串")
    selector = {
        "_id": ObjectId(loan_id),
        "status": {"$in": ["借出", "逾期"]},
        "return_date": {"$exists": False}
    }
    now = datetime.now(timezone.utc)
    loan = db.borrow_archive.find_one_and_update(
        selector,
        {"$set": {"status": "已归还", "return_date": now}},
        return_document=ReturnDocument.BEFORE
    )
    if loan is None:
        raise ValueError("借阅记录不存在或该书已经归还")
    stock_result = db.books.update_one(
        {"isbn": loan["book_isbn"]}, {"$inc": {"stock": 1}}
    )
    warnings = []
    if stock_result.matched_count == 0:
        warnings.append("原图书已不存在：归还状态已保存，请人工核对库存")
    # 时间序列集合不直接更新普通测量字段，用新增归还事件的方式登记。
    try:
        db.borrow_logs.insert_one({
            "borrow_date": now, "return_date": now,
            "original_borrow_date": loan["borrow_date"],
            "reader_card": loan["reader_card"],
            "book_isbn": loan["book_isbn"], "status": "已归还",
            "event_type": "归还", "archive_id": loan_id
        })
    except Exception as exc:
        warnings.append("时间序列归还事件写入失败：" + str(exc))
    try:
        db.book_logs.insert_one({"date": now, "action": "return",
                                 "isbn": loan["book_isbn"],
                                 "reader_card": loan["reader_card"]})
    except Exception as exc:
        warnings.append("审计日志写入失败：" + str(exc))
    return {"modified": 1,
            "stock_modified": stock_result.modified_count,
            "warnings": warnings}


def mark_overdue(db):
    """把普通归档集合中超过30天仍未归还的“借出”记录批量标记为“逾期”。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOAN_DAYS)
    result = db.borrow_archive.update_many(
        {
            "borrow_date": {"$lt": cutoff},
            "status": "借出",
            "return_date": {"$exists": False}
        },
        {"$set": {"status": "逾期"}}
    )
    return result.modified_count
