from pymongo import MongoClient
import sys
import os
from dotenv import load_dotenv

def update_users_visible_calendario():
    """
    Actualiza todos los documentos en la colección 'users' que no tienen
    el campo 'visible_calendario', estableciéndolo en True.
    Utiliza variables de entorno desde un archivo .env para la configuración.
    """
    try:
        # Cargar variables desde el archivo .env
        load_dotenv()
        
        # Obtener variables de entorno
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
        db_name = os.getenv('MONGO_DB')
        collection_name = os.getenv('MONGO_COLLECTION_NAME', 'usuarios')
        
        # Verificar que las variables necesarias estén definidas
        if not db_name:
            raise ValueError("La variable MONGO_DB_NAME no está definida en el archivo .env")
        
        # Establecer conexión con MongoDB
        client = MongoClient(mongo_uri)
        
        # Seleccionar la base de datos
        db = client[db_name]
        
        # Acceder a la colección de usuarios
        users_collection = db[collection_name]
        
        # Buscar documentos donde 'visible_calendario' no existe
        # y actualizar estableciendo 'visible_calendario' a True
        result = users_collection.update_many(
            {"visible_calendario": {"$exists": False}},
            {"$set": {"visible_calendario": True}}
        )
        
        print(f"Documentos encontrados: {result.matched_count}")
        print(f"Documentos actualizados: {result.modified_count}")
        
        # Cerrar la conexión
        client.close()
        
        return True
    
    except Exception as e:
        print(f"Error durante la actualización: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando actualización de usuarios...")
    if update_users_visible_calendario():
        print("Actualización completada con éxito.")
    else:
        print("La actualización falló.")
        sys.exit(1)