from app import db, User, Evento
from flask import Flask

# Crear contexto de aplicación para evitar errores
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendario.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def limpiar_datos():
    with app.app_context():
        # Eliminar todos los eventos de la base de datos
        num_eventos = Evento.query.delete()

        db.session.commit()
        print(f"✅ Se eliminaron {num_eventos} eventos de la base de datos.")

if __name__ == "__main__":
    confirmar = input("⚠️ ¿Seguro que quieres eliminar todos los datos de prueba? (Y/N): ")
    if confirmar.lower() == "y":
        limpiar_datos()
    else:
        print("❌ Operación cancelada.")
