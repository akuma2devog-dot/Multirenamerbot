import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["renamer"]
users = db["users"]

client.admin.command("ping")
print("✅ MongoDB connected")
