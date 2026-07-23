from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("MONGODB_DB_NAME", "orders_manager")]

GT_TEMPLATES = [
    {"template_id": "ordenes_gt_signup",   "title": "ÓRDENES GT — SIGNUP",    "phase": 0, "content": "", "tags": ["template", "ordenes", "gt"], "is_active": True},
    {"template_id": "ordenes_gt_defensas", "title": "ÓRDENES GT — DEFENSAS",  "phase": 1, "content": "", "tags": ["template", "ordenes", "gt"], "is_active": True},
    {"template_id": "ordenes_gt_ataque",   "title": "ÓRDENES GT — ATAQUE",    "phase": 2, "content": "", "tags": ["template", "ordenes", "gt"], "is_active": True},
    {"template_id": "ordenes_gt_cierre",   "title": "ÓRDENES GT — CIERRE",    "phase": 3, "content": "", "tags": ["template", "ordenes", "gt"], "is_active": True},
]

now = datetime.utcnow()

for doc in GT_TEMPLATES:
    doc["created_at"] = now
    doc["updated_at"] = now
    doc["bonus"] = {"zeffo": False, "mandalore": False}

    result = db["orders"].update_one(
        {"template_id": doc["template_id"]},
        {"$setOnInsert": doc},
        upsert=True,
    )

    if result.upserted_id:
        print(f"Creado: {doc['template_id']}")
    else:
        print(f"Ya existe: {doc['template_id']}")

print(f"\nDocumentos GT: {db['orders'].count_documents({'tags': 'gt'})}")
