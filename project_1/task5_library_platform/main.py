"""命令行主程序。进入项目目录后执行：python main.py"""
from datetime import datetime, timezone
from bson import json_util
from pymongo.errors import PyMongoError
from mongodb_connect import connect
import book_manager as bm
import reader_manager as rm
import borrow_manager as lm
import stat_manager as sm

MENU = """
======== 图书情报检索与统计平台 ========
 1. 检索图书             2. ISBN精确查找
 3. 添加图书             4. 修改库存
 5. 删除指定图书         6. 评分前5名
 7. 查询读者             8. 添加读者
 9. 学院人数统计        10. 读者等级统计
11. 登记借阅            12. 办理归还
13. 查看借阅记录        14. 查询未归还逾期
15. 分类综合统计        16. 年度借阅趋势
17. 热门图书排行        18. 活跃读者排行
19. 分类统计落库        20. 批量删除无库存图书
21. 批量标记未归还逾期
 0. 退出
=========================================
"""

def show(obj):
    if isinstance(obj, list):
        if not obj:
            print("没有找到符合条件的数据。")
            return
        print(f"查询成功：{len(obj)} 条")
        for item in obj:
            print(json_util.dumps(item, ensure_ascii=False, indent=2))
    elif obj is None:
        print("没有找到符合条件的数据。")
    else:
        print(json_util.dumps(obj, ensure_ascii=False, indent=2))

def number(prompt, kind=float, default=None):
    raw = input(prompt).strip()
    return default if not raw and default is not None else kind(raw)

def required(prompt):
    value = input(prompt).strip()
    if not value:
        raise ValueError("必填项不能为空")
    return value

def run_option(db, choice):
    if choice == "1":
        keyword = input("书名/作者/ISBN关键词（可空）: ").strip()
        cat = input("类别（可空）: ").strip()
        minprice = number("最低价格（默认0）: ", float, 0.0)
        show(bm.search_books(db, keyword=keyword, category=cat,
                             min_price=minprice))
    elif choice == "2":
        show(bm.find_by_isbn(db, required("ISBN: ")))
    elif choice == "3":
        book = {
            "isbn": required("新ISBN: "),
            "title": required("书名: "),
            "author": required("作者: "),
            "publisher": required("出版社: "),
            "category": required("类别: "),
            "price": number("价格: "),
            "stock": number("库存: ", int),
            "rating": number("评分0-5: "),
            "tags": [x.strip() for x in input("标签（逗号分隔，可空）: ").split(",")
                     if x.strip()]
        }
        ident = bm.add_book(db, book)
        print(f"插入成功：影响 1 条；_id={ident}")
    elif choice == "4":
        changed = bm.update_stock(db, required("ISBN: "),
                                  number("新库存: ", int))
        print(f"库存修改：影响 {changed} 条")
    elif choice == "5":
        isbn = required("要删除的 ISBN: ")
        if input("输入 YES 确认删除: ").strip() == "YES":
            print(f"删除成功：影响 {bm.delete_book(db, isbn)} 条")
        else:
            print("已取消。")
    elif choice == "6":
        show(bm.top_rated(db))
    elif choice == "7":
        card = input("借阅证号（留空显示全部读者）: ").strip()
        show(rm.get_reader(db, card) if card else rm.list_readers(db))
    elif choice == "8":
        card = required("新借阅证号: ")
        name = required("姓名: ")
        college = required("学院: ")
        email = input("邮箱（可空）: ").strip()
        phone = required("电话: ")
        level = required("等级（普通/高级/教师）: ")
        if level not in {"普通", "高级", "教师"}:
            raise ValueError("读者等级必须是普通、高级或教师")
        cats = [x.strip() for x in input("偏好类别（逗号分隔）: ").split(",")
                if x.strip()]
        print(f"读者新增成功：影响 1 条；_id={rm.add_reader(db, card, name, college, email, phone, level, cats)}")
    elif choice == "9":
        show(rm.college_stats(db))
    elif choice == "10":
        show(rm.level_stats(db))
    elif choice == "11":
        result = lm.register_borrow(db, required("借阅证号: "),
                                    required("图书ISBN: "))
        print(f"借阅成功：影响 {result['updated']} 条库存记录，借阅ID：{result['loan_id']}，剩余库存：{result['stock']}")
        for w in result["warnings"]:
            print("警告：", w)
    elif choice == "12":
        result = lm.return_book(db, required("借阅记录ID（菜单13查看）: "))
        print(f"归还成功：借阅记录影响 {result['modified']} 条；库存记录影响 {result['stock_modified']} 条")
        for w in result["warnings"]:
            print("警告：", w)
    elif choice == "13":
        show(lm.list_loans(db, input("借阅证号（可空）: ").strip()))
    elif choice == "14":
        show(lm.overdue_loans(db))
    elif choice == "15":
        show(sm.category_stats(db))
    elif choice == "16":
        show(sm.yearly_trend(db))
    elif choice == "17":
        show(sm.popular_books(db))
    elif choice == "18":
        show(sm.active_readers(db))
    elif choice == "19":
        print(f"已写入分类统计：{sm.save_category_stats(db)} 组")
    elif choice == "20":
        candidates = list(db.books.find(
            {"stock": 0}, {"_id": 0, "isbn": 1, "title": 1, "stock": 1}))
        show(candidates)
        if input("输入 DELETE_ZERO_STOCK 执行安全批量删除: ").strip() == "DELETE_ZERO_STOCK":
            print(f"已删除 {bm.delete_zero_stock_books(db)} 条（含未归还记录的图书自动排除）")
        else:
            print("已取消。")
    elif choice == "21":
        if input("将超过30天仍未归还的借出记录标记为逾期？输入 YES 确认: ").strip() == "YES":
            print(f"逾期状态更新：影响 {lm.mark_overdue(db)} 条借阅记录")
        else:
            print("已取消。")
    else:
        print("无效编号，请重新输入。")

def main():
    client = None
    try:
        client, db = connect()
        print("MongoDB 连接成功，数据库：library")
        for collection in ("books", "readers", "borrow_logs",
                           "borrow_archive", "category_stats"):
            print(f"{collection}: {db[collection].count_documents({})} 条")
        while True:
            print(MENU)
            choice = input("请选择功能编号: ").strip()
            if choice == "0":
                print("程序已正常退出。")
                break
            try:
                run_option(db, choice)
            except (ValueError, PyMongoError, TypeError) as exc:
                print("操作失败：", exc)
            except KeyboardInterrupt:
                print("\n当前操作已取消。")
    except PyMongoError as exc:
        print("数据库连接/认证失败：", exc)
    finally:
        if client is not None:
            client.close()
            print("数据库连接已关闭。")

if __name__ == "__main__":
    main()
