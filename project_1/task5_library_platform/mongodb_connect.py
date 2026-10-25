"""任务五统一连接模块：CentOS本机 MongoDB 9.0.2 / 27016 / library。"""
import getpass
import os
from pymongo import MongoClient

DATABASE_NAME = os.getenv("MONGO_DB", "library")

def connect():
    """返回 (client, db)；默认登录时交互式读取libWriter密码。"""
    uri = os.getenv("MONGO_URI", "").strip()
    if uri:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            tz_aware=True
        )
    else:
        user = os.getenv("MONGO_USER", "libWriter")
        password = os.getenv("MONGO_PASSWORD")
        options = {
            "host": os.getenv("MONGO_HOST", "127.0.0.1"),
            "port": int(os.getenv("MONGO_PORT", "27016")),
            "serverSelectionTimeoutMS": 5000,
            "tz_aware": True,
        }
        if user:
            if password is None:
                password = getpass.getpass(
                    f"请输入MongoDB用户 {user} 的密码（输入不回显）: "
                )
            options.update({
                "username": user,
                "password": password,
                "authSource": os.getenv("MONGO_AUTH_DB", "library")
            })
        client = MongoClient(**options)
    try:
        client.admin.command("ping")
        return client, client[DATABASE_NAME]
    except Exception:
        client.close()
        raise
