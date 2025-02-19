from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Conectar a MongoDB
client = MongoClient(MONGO_URI)
db = client["calendario"]
users_collection = db["usuarios"]

# Obtener todos los usuarios
usuarios = list(users_collection.find())

if not usuarios:
    print("❌ No hay usuarios en la base de datos.")
else:
    print("📌 Creando nuevos documentos con ObjectId...")

    for usuario in usuarios:
        if not isinstance(usuario["_id"], ObjectId):  # Si el ID no es un ObjectId
            nuevo_usuario = usuario.copy()  # Copiar datos del usuario
            nuevo_usuario["_id"] = ObjectId()  # Generar nuevo ObjectId

            users_collection.insert_one(nuevo_usuario)  # Insertar nuevo documento
            users_collection.delete_one({"_id": usuario["_id"]})  # Eliminar documento antiguo

            print(f"✅ Usuario {usuario['usuario']} corregido con nuevo ID {nuevo_usuario['_id']}")

    print("🎉 Todos los usuarios tienen ObjectId.")
