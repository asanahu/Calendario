from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["calendario"]
users_collection = db["usuarios"]

# Define una contraseña por defecto, por ejemplo "password123"
default_password = "password123"
hashed_password = generate_password_hash(default_password)

# Actualiza cada usuario que no tenga el campo "password"
result = users_collection.update_many(
    {"password": {"$exists": False}},
    {"$set": {"password": hashed_password}}
)

print(f"Se han actualizado {result.modified_count} usuarios.")
