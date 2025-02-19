from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
from pymongo import MongoClient
from bson import ObjectId
import os

# Cargar variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Conectar a MongoDB
client = MongoClient(MONGO_URI)
db = client["calendario"]
users_collection = db["usuarios"]
events_collection = db["eventos"]

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.nombre = user_data['nombre']
        self.apellidos = user_data['apellidos']
        self.usuario = user_data['usuario']
        self.puesto = user_data['puesto']

@login_manager.user_loader
def load_user(user_id):
    """ Cargar usuario desde MongoDB por ID """
    from bson import ObjectId
    try:
        user_data = users_collection.find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None
    except Exception as e:
        print(f"Error al cargar usuario {user_id}: {e}")
        return None

# Decorador para restringir acceso a administradores
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.puesto != "Administrador/a":
            abort(403)
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
def home():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form['usuario']
        user_data = users_collection.find_one({"usuario": usuario_input})

        if not user_data:
            return "Usuario no autorizado", 401
        
        user = User(user_data)
        user.id = str(user_data["_id"])  # Asegurar que el ID sea string
        login_user(user)
        return redirect(url_for('calendar_page'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/calendar')
@login_required
def calendar_page():
    return render_template('index.html')

def get_color_by_puesto(puesto):
    clases = {
        "TS": "ts-event",
        "ADM": "adm-event",
        "Administrador/a": "administrador-event",
    }
    return clases.get(puesto, "default-event")  # 🔹 Si el puesto no está en la lista, usa una clase por defecto


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    usuarios = list(users_collection.find().sort("nombre"))
    return render_template('admin_users.html', usuarios=usuarios)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        user_data = {
            "nombre": request.form.get('nombre'),
            "apellidos": request.form.get('apellidos'),
            "usuario": request.form.get('usuario'),
            "puesto": request.form.get('puesto')
        }
        if users_collection.find_one({"usuario": user_data["usuario"]}):
            return "El usuario ya existe", 400
        users_collection.insert_one(user_data)
        return redirect('/admin/users')
    return render_template('add_user.html')

@app.route('/admin/delete_user/<user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    usuario = users_collection.find_one({"_id": ObjectId(user_id)})

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    # 🚨 No permitir que un administrador se elimine a sí mismo
    if usuario["usuario"] == current_user.usuario:
        return jsonify({"message": "No puedes eliminarte a ti mismo"}), 403

    users_collection.delete_one({"_id": ObjectId(user_id)})
    return redirect('/admin/users')

@app.route('/admin/user_vacations/<user_id>')
@login_required
@admin_required
def user_vacations(user_id):
    usuario = users_collection.find_one({"_id": ObjectId(user_id)})
    if not usuario:
        abort(404)

    # 🔹 Obtener las vacaciones, ordenarlas por fecha de inicio (ascendente)
    vacaciones = list(events_collection.find(
        {"trabajador": f"{usuario['nombre']} {usuario['apellidos']}", "tipo": "Vacaciones"}
    ).sort("fecha_inicio", 1))  # 1 = Orden ascendente

    # 🔹 Convertir fechas al formato DD/MM/YYYY
    for vacacion in vacaciones:
        vacacion["fecha_inicio"] = datetime.strptime(vacacion["fecha_inicio"], "%Y-%m-%d").strftime("%d/%m/%Y")
        vacacion["fecha_fin"] = datetime.strptime(vacacion["fecha_fin"], "%Y-%m-%d").strftime("%d/%m/%Y")

    return render_template('user_vacations.html', usuario=usuario, vacaciones=vacaciones)


@app.route('/add-vacation', methods=['GET', 'POST'])
@login_required
def add_vacation():
    if request.method == 'POST':
        vacation_data = {
            "trabajador": f"{current_user.nombre} {current_user.apellidos}",
            "fecha_inicio": request.form.get('fecha_inicio'),
            "fecha_fin": request.form.get('fecha_fin'),
            "tipo": "Vacaciones"
        }
        events_collection.insert_one(vacation_data)
        return redirect('/add-vacation')

    # 🔹 Obtener y convertir las fechas de string a datetime antes de enviarlas a la plantilla
    vacaciones = list(events_collection.find({
        "trabajador": f"{current_user.nombre} {current_user.apellidos}",
        "tipo": "Vacaciones"
    }).sort("fecha_inicio", 1))  # ✅ Ordenar por fecha de inicio

    for vacacion in vacaciones:
        vacacion["fecha_inicio"] = datetime.strptime(vacacion["fecha_inicio"], "%Y-%m-%d")
        vacacion["fecha_fin"] = datetime.strptime(vacacion["fecha_fin"], "%Y-%m-%d")

    return render_template('add_vacation.html', vacaciones=vacaciones)



@app.route('/delete-vacation/<vacation_id>', methods=['POST'])
@login_required
def delete_vacation(vacation_id):
    try:

        # Convertir el ID en ObjectId solo si es válido
        if not ObjectId.is_valid(vacation_id):
            print("❌ ID no válido para MongoDB")
            return jsonify({"message": "ID no válido"}), 400

        result = events_collection.delete_one({"_id": ObjectId(vacation_id)})

        if result.deleted_count == 0:
            print("❌ Vacación no encontrada en la base de datos")
            return jsonify({"message": "Vacación no encontrada"}), 404

        return redirect('/add-vacation')
    except Exception as e:
        print(f"⚠️ Error al eliminar la vacación: {e}")
        return jsonify({"message": "Error interno"}), 500

@app.route('/api/events', methods=['GET', 'POST'])
@login_required
def events():
    if request.method == 'POST':
        event_data = request.get_json()
        event_data["trabajador"] = f"{current_user.nombre} {current_user.apellidos}"
        events_collection.insert_one(event_data)
        return jsonify({"message": "Evento agregado correctamente"}), 201

    # 🔹 Lista de festivos
    festivos = {
        "2025-01-01", "2025-01-06", "2025-01-29", "2025-03-05", "2025-03-28", "2025-03-29",
        "2025-04-23", "2025-05-01", "2025-08-15", "2025-10-12", "2025-11-01", "2025-12-06",
        "2025-12-09", "2025-12-25", "2026-01-01"
    }

    # 🔹 Definir el orden de los puestos
    orden_puestos = {"Administrador/a": 1, "ADM": 2, "TS": 3}
    colores_puestos = {
        "Administrador/a": "#FFD700",
        "ADM": "#B0FFB0",
        "TS": "#A3C4FF"
    }

    # 🔹 Obtener todos los usuarios y aplicar orden por puesto
    usuarios = list(users_collection.find())
    usuarios_ordenados = sorted(usuarios, key=lambda u: orden_puestos.get(u.get("puesto", ""), 4))

    # 🔹 Obtener todas las vacaciones registradas
    eventos = list(events_collection.find())

    # 🔹 Estructura para agrupar vacaciones por trabajador
    dias_no_disponibles = {}
    for evento in eventos:
        nombre = evento["trabajador"]
        if nombre not in dias_no_disponibles:
            dias_no_disponibles[nombre] = []
        dias_no_disponibles[nombre].append((evento["fecha_inicio"], evento["fecha_fin"]))

    eventos_json = []
    contador_disponibles = {}

    # 🔹 Generar eventos desde el 1 de enero hasta el 31 de diciembre de 2025
    fecha_actual = datetime(2025, 1, 1)
    fecha_fin = datetime(2025, 12, 31)

    while fecha_actual <= fecha_fin:
        fecha_str = fecha_actual.strftime("%Y-%m-%d")
        dia_semana = fecha_actual.weekday()

        # ✅ Agregar los festivos como eventos especiales
        if fecha_str in festivos:
            eventos_json.append({
                "id": f"Festivo-{fecha_str}",
                "title": "Festivo",
                "start": fecha_str,
                "color": "#FFD700",
                "classNames": ["festivo-event"]
            })
            contador_disponibles[fecha_str] = 0

        # ✅ Solo mostrar eventos de lunes a viernes
        elif dia_semana < 5:
            disponibles_en_dia = 0
            eventos_dia = []

            for usuario in usuarios_ordenados:
                nombre_completo = f"{usuario['nombre']} {usuario['apellidos']}"
                color = colores_puestos.get(usuario["puesto"], "#D3D3D3")

                # ¿Está el trabajador de vacaciones ese día?
                tiene_vacaciones = any(
                    fecha_str >= inicio and fecha_str <= fin
                    for inicio, fin in dias_no_disponibles.get(nombre_completo, [])
                )

                eventos_dia.append({
                    "id": f"{nombre_completo}-{fecha_str}",
                    "title": f"{usuario['puesto']} - {nombre_completo} (Ausente)" if tiene_vacaciones else f"{usuario['puesto']} - {nombre_completo}",
                    "start": fecha_str,
                    "color": "#FF0000" if tiene_vacaciones else color
                })

                if not tiene_vacaciones:
                    disponibles_en_dia += 1

            # 🔹 Asegurar que el orden se respete dentro de cada día
            eventos_dia.sort(key=lambda e: orden_puestos.get(e["title"].split(" - ")[0], 4))
            eventos_json.extend(eventos_dia)
            contador_disponibles[fecha_str] = disponibles_en_dia  

        fecha_actual += timedelta(days=1)

    return jsonify({"eventos": eventos_json, "contador": contador_disponibles})

@app.route('/api/events/<event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    evento = events_collection.find_one({"_id": ObjectId(event_id)})
    if not evento:
        return jsonify({"message": "Evento no encontrado"}), 404

    if evento["trabajador"] != f"{current_user.nombre} {current_user.apellidos}":
        return jsonify({"message": "No puedes eliminar eventos de otros"}), 403

    events_collection.delete_one({"_id": ObjectId(event_id)})
    return jsonify({"message": "Evento eliminado, el usuario vuelve a estar disponible"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
