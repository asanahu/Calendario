from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGO_URI")
client = MongoClient(uri)
db = client["calendario"]
collection = db["eventos"]

# Update Baja -> Ausencia
result1 = collection.update_many(
    {
        "tipo": {"$in": ["Baja", "Baja Medica", "Baja Médica"]}, 
        "fecha_inicio": {"$gte": "2026-01-01"}
    },
    {"$set": {"tipo": "Ausencia"}}
)

print(f"Fixed {result1.modified_count} entries (Baja -> Ausencia).")
