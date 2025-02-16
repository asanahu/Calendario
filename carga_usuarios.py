from app import db, User, Evento
from flask import Flask
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from usuarios import usuarios

# Crear contexto de aplicación para evitar errores
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def cargar_usuarios():
    with app.app_context():
        for u in usuarios:
            if not User.query.filter_by(usuario=u["usuario"]).first():
                nuevo_usuario = User(nombre=u["nombre"], apellidos=u["apellidos"], usuario=u["usuario"], puesto=u["puesto"])
                db.session.add(nuevo_usuario)
        
        db.session.commit()
        print("✅ Usuarios cargados correctamente en la base de datos.")

if __name__ == "__main__":
    cargar_usuarios()
