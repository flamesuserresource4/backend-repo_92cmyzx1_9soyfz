import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="Coffee Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Coffee Shop API is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# Seed menu items if none exist
@app.post("/api/seed")
def seed_products():
    existing = list(db["product"].find({})) if db else []
    if existing:
        return {"seeded": False, "count": len(existing)}

    default_products = [
        {"title": "Espresso", "description": "Rich and bold shot", "price": 3.0, "category": "coffee", "in_stock": True, "image": "https://images.unsplash.com/photo-1511920170033-f8396924c348"},
        {"title": "Americano", "description": "Espresso with hot water", "price": 3.5, "category": "coffee", "in_stock": True, "image": "https://images.unsplash.com/photo-1503481766315-7a586b20f66b"},
        {"title": "Cappuccino", "description": "Espresso with steamed milk foam", "price": 4.0, "category": "coffee", "in_stock": True, "image": "https://images.unsplash.com/photo-1527167765609-5ff6f4cfb9cf"},
        {"title": "Latte", "description": "Espresso with steamed milk", "price": 4.5, "category": "coffee", "in_stock": True, "image": "https://images.unsplash.com/photo-1453614512568-c4024d13c247"},
        {"title": "Mocha", "description": "Chocolate + espresso + milk", "price": 4.75, "category": "coffee", "in_stock": True, "image": "https://images.unsplash.com/photo-1498804103079-a6351b050096"},
        {"title": "Croissant", "description": "Buttery flaky pastry", "price": 3.25, "category": "bakery", "in_stock": True, "image": "https://images.unsplash.com/photo-1509440159596-0249088772ff"}
    ]

    inserted = 0
    for p in default_products:
        create_document("product", p)
        inserted += 1
    return {"seeded": True, "count": inserted}

@app.get("/api/menu", response_model=List[Product])
def get_menu():
    docs = get_documents("product")
    # Convert ObjectId to str for image-safe return; Product doesn't include _id so it's fine
    items = []
    for d in docs:
        d.pop("_id", None)
        items.append(Product(**d))
    return items

class CreateOrder(BaseModel):
    customer_name: str
    items: List[OrderItem]

@app.post("/api/orders")
def create_order(order: CreateOrder):
    # Compute total
    total = sum(item.price * item.quantity for item in order.items)
    record = Order(customer_name=order.customer_name, items=order.items, total=total, status="pending")
    oid = create_document("order", record)
    return {"ok": True, "order_id": oid, "total": total}

@app.get("/api/orders")
def list_orders():
    docs = get_documents("order")
    # Clean ObjectId for JSON safety
    for d in docs:
        if isinstance(d.get("_id"), ObjectId):
            d["_id"] = str(d["_id"])
        # Convert nested items keys if present
        if "items" in d and isinstance(d["items"], list):
            for it in d["items"]:
                if isinstance(it.get("product_id"), ObjectId):
                    it["product_id"] = str(it["product_id"])
    return {"orders": docs}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
