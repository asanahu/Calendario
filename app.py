from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import text
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirigir automáticamente a login

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    puesto = db.Column(db.String(100), nullable=False)  # 🔹 Nuevo campo para el puesto



class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trabajador = db.Column(db.String(100), nullable=False)
    fecha_inicio = db.Column(db.String(10), nullable=False)
    fecha_fin = db.Column(db.String(10), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # Vacaciones, Libre, etc.

def admin_required(func):
    """ Decorador para restringir acceso solo a Administradores """
    @wraps(func)  # 🔹 Esto evita que Flask detecte funciones con el mismo nombre
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.puesto != "Administrador/a":
            abort(403)  # ⛔ Prohibido si no es administrador/a
        return func(*args, **kwargs)
    return wrapper

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        logout_user()  # 🔹 Cierra la sesión de cualquier usuario activo
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form['usuario']  # 🔹 Usuario ingresado por el trabajador
        usuario = User.query.filter_by(usuario=usuario_input).first()

        if not usuario:
            return "Usuario no autorizado", 401  # 🔴 Si el usuario no está en la lista, denegar acceso

        login_user(usuario)
        return redirect(url_for('calendar_page'))  # 🔹 Si existe, entra al calendario

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/calendar')
@login_required  #Solo usuarios logueados pueden acceder
def calendar_page():
    return render_template('index.html')

def get_color_by_puesto(puesto):
    colores = {
        "TS": "#A3C4FF",  # 🔹 Azul claro
        "ADM": "#B0FFB0",  # 🔹 Verde claro
        "Administrador/a": "#FFFF00",  # 🔹 Amarillo
    }
    return colores.get(puesto, "#D3D3D3")  # 🔹 Gris claro por defecto

@app.route('/admin/users')
@login_required
def admin_users():
    # Verificar si el usuario tiene permisos de administrador
    if current_user.puesto.lower() != "administrador/a":
        return redirect('/calendar')

    # 🔹 Obtener usuarios ordenados alfabéticamente por nombre
    usuarios = User.query.order_by(User.nombre).all()

    return render_template('admin_users.html', usuarios=usuarios)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        usuario = request.form.get('usuario')
        puesto = request.form.get('puesto')

        if not User.query.filter_by(usuario=usuario).first():
            nuevo_usuario = User(
                nombre=nombre, 
                apellidos=apellidos, 
                usuario=usuario, 
                puesto=puesto
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            return redirect('/admin/users')

    return render_template('add_user.html')

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    usuario = db.session.get(User, user_id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
    return redirect('/admin/users')

@app.route('/admin/user_vacations/<int:user_id>')
@login_required
@admin_required
def user_vacations(user_id):
    usuario = db.session.get(User, user_id)  # ✅ Obtener el usuario
    if not usuario:
        abort(404)  # ⛔ Error si el usuario no existe

    vacaciones = Evento.query.filter_by(trabajador=f"{usuario.nombre} {usuario.apellidos}", tipo="Vacaciones").all()

    return render_template('user_vacations.html', usuario=usuario, vacaciones=vacaciones)


@app.route('/add-vacation', methods=['GET', 'POST'])
@login_required
def add_vacation():
    if request.method == 'POST':
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')

        if not fecha_inicio or not fecha_fin:
            return jsonify({"message": "Fechas inválidas"}), 400

        nombre_completo = f"{current_user.nombre} {current_user.apellidos}"  
        
        # Registrar las vacaciones
        nueva_vacacion = Evento(
            trabajador=nombre_completo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo="Vacaciones"
        )
        db.session.add(nueva_vacacion)
        db.session.commit()

        return redirect('/add-vacation')  # 🔹 Volver a la misma página después de añadir

    # 🔹 Obtener vacaciones del usuario actual, ordenadas cronológicamente
    nombre_completo = f"{current_user.nombre} {current_user.apellidos}"
    vacaciones = Evento.query.filter_by(trabajador=nombre_completo, tipo="Vacaciones") \
                             .order_by(Evento.fecha_inicio).all()  # 🔹 Ordenar por fecha de inicio

    # 🔹 Convertir fechas a formato datetime si son strings
    for vacacion in vacaciones:
        if isinstance(vacacion.fecha_inicio, str):
            vacacion.fecha_inicio = datetime.strptime(vacacion.fecha_inicio, '%Y-%m-%d')
        if isinstance(vacacion.fecha_fin, str):
            vacacion.fecha_fin = datetime.strptime(vacacion.fecha_fin, '%Y-%m-%d')

    return render_template('add_vacation.html', vacaciones=vacaciones)

@app.route('/delete-vacation/<int:vacation_id>', methods=['POST'])
@login_required
def delete_vacation(vacation_id):
    vacacion = db.session.get(Evento, vacation_id)
    
    if vacacion and vacacion.trabajador == f"{current_user.nombre} {current_user.apellidos}":
        db.session.delete(vacacion)
        db.session.commit()
    
    return redirect('/add-vacation')  # 🔹 Volver a la página de añadir vacaciones


@app.route('/api/events', methods=['GET', 'POST'])
@login_required
def events():
    if request.method == 'POST':  # 🔹 Si se están añadiendo vacaciones
        if request.is_json:
            data = request.get_json()
            fecha_inicio = data.get("fecha_inicio")
            fecha_fin = data.get("fecha_fin")
        else:
            fecha_inicio = request.form.get('fecha_inicio')
            fecha_fin = request.form.get('fecha_fin')

        if not fecha_inicio or not fecha_fin:
            return jsonify({"message": "Fechas inválidas"}), 400

        nombre_completo = f"{current_user.nombre} {current_user.apellidos}"  

        # Registrar vacaciones en la base de datos
        nuevo_evento = Evento(trabajador=nombre_completo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, tipo="Vacaciones")

        db.session.add(nuevo_evento)
        db.session.commit()

        return redirect('/calendar')

    # 🔹 Obtener los usuarios y las vacaciones registradas
    usuarios = User.query.all()
    vacaciones = Evento.query.all()
    dias_no_disponibles = {}

    for v in vacaciones:
        if v.trabajador not in dias_no_disponibles:
            dias_no_disponibles[v.trabajador] = []
        dias_no_disponibles[v.trabajador].append((v.fecha_inicio, v.fecha_fin))

    # 🔹 Definir los festivos
    festivos = {
        "2025-01-01", "2025-01-06", "2025-01-29", "2025-03-05", "2025-03-28", "2025-03-29",
        "2025-04-23", "2025-05-01", "2025-08-15", "2025-10-12", "2025-11-01", "2025-12-06",
        "2025-12-09", "2025-12-25", 
        "2026-01-01"  # 🔹 Añadir Año Nuevo 2026
    }

    # Definir el orden de los puestos
    orden_puestos = {"Administrador/a": 1, "ADM": 2, "TS": 3}
    usuarios_ordenados = sorted(usuarios, key=lambda u: orden_puestos.get(u.puesto, 4))

    eventos_json = []
    contador_disponibles = {}

    # 🔹 Ampliamos la generación de eventos hasta enero de 2026
    fecha_inicio = datetime(2025, 1, 1)
    fecha_fin = datetime(2026, 1, 31)  # 🔹 Incluir enero de 2026

    while fecha_inicio <= fecha_fin:
        fecha_str = fecha_inicio.strftime('%Y-%m-%d')
        dia_semana = fecha_inicio.weekday()

        if fecha_str in festivos:
            eventos_json.append({
                "id": f"Festivo-{fecha_str}",
                "title": "Festivo",
                "start": fecha_str,
                "color": "#FFCC00",  # 🔹 Amarillo para festivos
                "classNames": ["festivo-event"]
            })
            contador_disponibles[fecha_str] = 0  # 🔹 Ningún trabajador disponible en festivos

        elif dia_semana < 5:  # 🔹 Solo de lunes a viernes
            disponibles_en_dia = 0

            for usuario in usuarios_ordenados:
                nombre_completo = f"{usuario.nombre} {usuario.apellidos}"
                color = get_color_by_puesto(usuario.puesto)  
                vacaciones_color = "#FF0000"  # 🔹 Rojo para vacaciones

                # Verificar si el usuario tiene vacaciones en este día
                tiene_vacaciones = any(
                    fecha_str >= inicio and fecha_str <= fin
                    for inicio, fin in dias_no_disponibles.get(nombre_completo, [])
                )

                eventos_json.append({
                    "id": f"{nombre_completo}-{fecha_str}",
                    "title": f"{usuario.puesto} - {nombre_completo} (Ausente)" if tiene_vacaciones else f"{usuario.puesto} - {nombre_completo}",
                    "start": fecha_str,
                    "color": vacaciones_color if tiene_vacaciones else color,
                    "classNames": ["vacaciones-event"] if tiene_vacaciones else []  # 🔹 Aplica la clase CSS solo a vacaciones
                })

                if not tiene_vacaciones:
                    disponibles_en_dia += 1  

            contador_disponibles[fecha_str] = disponibles_en_dia  

        fecha_inicio += timedelta(days=1)

    return jsonify({"eventos": eventos_json, "contador": contador_disponibles})

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    evento = Evento.query.get(event_id)
    if not evento:
        return jsonify({"message": "Evento no encontrado"}), 404

    if evento.trabajador != f"{current_user.nombre} {current_user.apellidos}":
        return jsonify({"message": "No puedes eliminar eventos de otros"}), 403  # 🔹 Proteger eventos de otros usuarios

    db.session.delete(evento)
    db.session.commit()

    return jsonify({"message": "Evento eliminado, el usuario vuelve a estar disponible"}), 200

@app.route('/api/events', methods=['POST'])
@login_required
def add_event():
    # Si la solicitud es JSON (desde FullCalendar.js)
    if request.is_json:
        data = request.get_json()
        fecha_inicio = data.get("fecha_inicio")
        fecha_fin = data.get("fecha_fin")

    # Si la solicitud es desde un formulario HTML (form-data)
    else:
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')

    # Validar que las fechas no estén vacías
    if not fecha_inicio or not fecha_fin:
        return jsonify({"message": "Fechas inválidas"}), 400

    # Crear el evento
    nuevo_evento = Evento(trabajador=current_user.nombre, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, tipo="Vacaciones")
    db.session.add(nuevo_evento)
    db.session.commit()

    # Redirigir al calendario si la solicitud es desde el formulario
    if not request.is_json:
        return redirect(url_for('calendar_page'))

    return jsonify({"message": "Evento agregado correctamente"}), 201  # Respuesta para JSON (FullCalendar.js)



def clear_sessions():
    with app.app_context():
        try:
            db.session.execute(text("DELETE FROM flask_session"))  # 🔹 Corregido con text()
            db.session.commit()
        except Exception as e:
            print("No se pudo eliminar sesiones:", e)





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
