from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson.json_util import dumps

load_dotenv()
uri = os.getenv("MONGO_URI")
if not uri:
    print("No MONGO_URI found")
    exit(1)

client = MongoClient(uri)
db = client["calendario"]
events = db["eventos"]

# Check distinct types
print("--- Distinct Types ---")
print(events.distinct("tipo"))

# Check Jan 13, 14, 15
print("\n--- Jan 13-15 (Baja Check) ---")
dates = ["2026-01-13", "2026-01-14", "2026-01-15"]
cursor = events.find({"fecha_inicio": {"$in": dates}, "tipo": {"$regex": "Baja|Ausencia"}})
for doc in cursor:
    print(f"{doc['fecha_inicio']} - {doc['trabajador']} - Type: '{doc.get('tipo')}'")

# Check Jan 27 (Sara Clavero)
print("\n--- Jan 27 (Sara Clavero Check) ---")
cursor_sara = events.find({"fecha_inicio": "2026-01-27", "trabajador": {"$regex": "Sara"}})
for doc in cursor_sara:
    print(f"{doc['fecha_inicio']} - {doc['trabajador']} - Type: '{doc.get('tipo')}'")
