from pymongo import MongoClient
import os
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Conectar a MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["calendario"]
users_collection = db["usuarios"]  # Colección para usuarios

# Cargar usuarios desde el JSON
def cargar_usuarios():
    with open("usuarios.json", "r", encoding="utf-8") as file:
        usuarios = json.load(file)

    for u in usuarios:
        # Verificar si el usuario ya existe en la base de datos
        if users_collection.find_one({"usuario": u["usuario"]}) is None:
            users_collection.insert_one(u)  # Insertar usuario en MongoDB

    print("✅ Usuarios cargados correctamente en la base de datos.")

if __name__ == "__main__":
    cargar_usuarios()
