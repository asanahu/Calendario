from app import db, User, Evento
from flask import Flask
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from usuarios import usuarios
import json
# Crear contexto de aplicación para evitar errores
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# 🔹 Obtener los usuarios desde la variable de entorno
usuarios_json = os.getenv("USUARIOS_JSON")

if usuarios_json:
    usuarios = json.loads(usuarios_json)
    
    # 🔹 Guardar usuarios en un archivo temporal `usuarios.py`
    with open("usuarios.py", "w", encoding="utf-8") as f:
        f.write(f"usuarios = {json.dumps(usuarios, indent=4)}\n")

    print("✅ `usuarios.py` generado automáticamente desde variables de entorno.")
else:
    print("⚠️ No se encontró la variable de entorno `USUARIOS_JSON`")


"""def cargar_usuarios():
    with app.app_context():
        for u in usuarios:
            if not User.query.filter_by(usuario=u["usuario"]).first():
                nuevo_usuario = User(nombre=u["nombre"], apellidos=u["apellidos"], usuario=u["usuario"], puesto=u["puesto"])
                db.session.add(nuevo_usuario)
        
        db.session.commit()
        print("✅ Usuarios cargados correctamente en la base de datos.")"""

if __name__ == "__main__":
    cargar_usuarios()
