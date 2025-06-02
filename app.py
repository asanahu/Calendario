from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import datetime
import boto3
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from functools import wraps
from pymongo import MongoClient
from bson import ObjectId
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import time
import uuid

# Cargar variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_S3_REGION = os.getenv("AWS_S3_REGION")

# Conectar a MongoDB
client = MongoClient(MONGO_URI)
db = client["calendario"]
users_collection = db["usuarios"]
events_collection = db["eventos"]
historial_collection = db["historial_conversaciones"]


# Inicializar el cliente de boto3
s3_client = boto3.client(
    's3',
    region_name=AWS_S3_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

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

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/calendar')
@login_required
def calendar_page():
    # Obtener todos los usuarios visibles
    usuarios = list(users_collection.find(
        {"visible_calendario": {"$ne": False}},
        {"nombre": 1, "apellidos": 1}
    ))
    
    # Convertir ObjectId a string para serialización JSON
    for usuario in usuarios:
        usuario['_id'] = str(usuario['_id'])
    
    # Ordenar usuarios por nombre
    usuarios_ordenados = sorted(
        usuarios, 
        key=lambda x: f"{x['nombre']} {x['apellidos']}".lower()
    )
    return render_template('index.html', usuarios=usuarios_ordenados)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form['usuario']
        password_input = request.form['password']
        user_data = users_collection.find_one({"usuario": usuario_input})

        if user_data is None or not check_password_hash(user_data.get("password", ""), password_input):
            flash("Usuario o contraseña incorrectos", "error")
            return redirect(url_for('login'))
        
        user = User(user_data)
        user.id = str(user_data["_id"])  # Asegurar que el ID sea string
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

"""
@app.route('/calendar')
@login_required
def calendar_page():
    return render_template('index.html')
"""
@app.route('/ai-assistant')
@login_required
def ai_assistant():
    return render_template('ai_assistant.html')


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
        password = request.form.get('password')
        visible = request.form.get('visible_calendario')

        # Si necesitas convertir visible a booleano:
        visible = True if visible.lower() == "true" else False
        
        user_data = {
            "nombre": request.form.get('nombre'),
            "apellidos": request.form.get('apellidos'),
            "usuario": request.form.get('usuario'),
            "puesto": request.form.get('puesto'),
            "password": generate_password_hash(password),
            "visible_calendario": visible
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

@app.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Obtener el usuario actual desde la BD
        user_data = users_collection.find_one({"_id": ObjectId(current_user.id)})
        
        # Verificar que la contraseña actual sea correcta
        if not check_password_hash(user_data.get("password", ""), current_password):
            flash("La contraseña actual es incorrecta", "error")
            return redirect(url_for('cambiar_password'))
        
        # Verificar que la nueva contraseña y su confirmación coincidan
        if new_password != confirm_password:
            flash("La nueva contraseña y la confirmación no coinciden", "error")
            return redirect(url_for('cambiar_password'))
        
        # Generar el hash de la nueva contraseña y actualizar la BD
        new_hashed_password = generate_password_hash(new_password)
        users_collection.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": {"password": new_hashed_password}}
        )
        flash("Contraseña actualizada exitosamente", "success")
        return redirect(url_for('dashboard'))
    
    return render_template("cambiar_password.html")

def agrupar_vacaciones(vacaciones):
    """
    Agrupa las vacaciones consecutivas. Se asume que la lista 'vacaciones' está ordenada por 'fecha_inicio'.
    Cada grupo es una lista de vacaciones consecutivas, donde la fecha de inicio de una vacación
    es exactamente un día después de la fecha de fin de la vacación anterior.
    """
    grupos = []
    grupo_actual = []
    for vacacion in vacaciones:
        if not grupo_actual:
            grupo_actual.append(vacacion)
        else:
            ultimo = grupo_actual[-1]
            # Comprobamos si la vacación actual es consecutiva con respecto al grupo actual.
            if vacacion["fecha_inicio"] == ultimo["fecha_fin"] + timedelta(days=1):
                grupo_actual.append(vacacion)
            else:
                grupos.append(grupo_actual)
                grupo_actual = [vacacion]
    if grupo_actual:
        grupos.append(grupo_actual)
    return grupos

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
        # Convertir las fechas a objetos datetime para iterar día a día
        fecha_inicio_dt = datetime.strptime(vacation_data["fecha_inicio"], "%Y-%m-%d")
        fecha_fin_dt = datetime.strptime(vacation_data["fecha_fin"], "%Y-%m-%d")
        
        # Insertar un evento por cada día en el rango
        current_day = fecha_inicio_dt
        while current_day <= fecha_fin_dt:
            day_str = current_day.strftime("%Y-%m-%d")
            event = {
                "trabajador": vacation_data["trabajador"],
                "fecha_inicio": day_str,
                "fecha_fin": day_str,
                "tipo": "Vacaciones"
            }
            events_collection.insert_one(event)
            current_day += timedelta(days=1)
        return redirect('/add-vacation')
    
    # Obtener las vacaciones existentes para el usuario, ordenadas por fecha de inicio
    vacaciones = list(events_collection.find({
        "trabajador": f"{current_user.nombre} {current_user.apellidos}",
        "tipo": "Vacaciones"
    }).sort("fecha_inicio", 1))
    
    # Convertir los strings de fechas a objetos datetime
    for vacacion in vacaciones:
        vacacion["fecha_inicio"] = datetime.strptime(vacacion["fecha_inicio"], "%Y-%m-%d")
        vacacion["fecha_fin"] = datetime.strptime(vacacion["fecha_fin"], "%Y-%m-%d")
    
    # Agrupar las vacaciones consecutivas
    grupos_vacaciones = agrupar_vacaciones(vacaciones)
    
    return render_template('add_vacation.html', grupos_vacaciones=grupos_vacaciones)

@app.route('/admin/user_vacations/<user_id>')
@login_required
@admin_required
def user_vacations(user_id):
    usuario = users_collection.find_one({"_id": ObjectId(user_id)})
    if not usuario:
        abort(404)

    # Obtener las vacaciones, ordenadas por fecha de inicio (ascendente)
    vacaciones = list(events_collection.find(
        {"trabajador": f"{usuario['nombre']} {usuario['apellidos']}", "tipo": "Vacaciones"}
    ).sort("fecha_inicio", 1))

    # Convertir las fechas de string a objetos datetime
    for vacacion in vacaciones:
        vacacion["fecha_inicio"] = datetime.strptime(vacacion["fecha_inicio"], "%Y-%m-%d")
        vacacion["fecha_fin"] = datetime.strptime(vacacion["fecha_fin"], "%Y-%m-%d")

    # Agrupar las vacaciones consecutivas
    grupos_vacaciones = agrupar_vacaciones(vacaciones)

    return render_template('user_vacations.html', usuario=usuario, grupos_vacaciones=grupos_vacaciones)

@app.route('/delete-vacation/<vacation_id>', methods=['POST'])
@login_required
def delete_vacation(vacation_id):
    try:
        # 🔹 Asegurar que el ID sea un ObjectId válido
        if not ObjectId.is_valid(vacation_id):
            print("❌ ID no válido para MongoDB")
            return jsonify({"error": "ID no válido"}), 400

        query = {"_id": ObjectId(vacation_id)}
        vacacion = events_collection.find_one(query)

        if vacacion and vacacion["trabajador"] == f"{current_user.nombre} {current_user.apellidos}":
            events_collection.delete_one(query)
            print("✅ Vacación eliminada correctamente")
            return redirect('/add-vacation')
        else:
            print("⚠️ No tienes permiso para eliminar esta vacación")
            return jsonify({"error": "No autorizado"}), 403

    except Exception as e:
        print(f"⚠️ Error al eliminar la vacación: {e}")
        return jsonify({"error": "Error interno"}), 500
    
    
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
        "2025-12-09", "2025-12-25", "2026-01-01", "2025-04-17", "2025-04-18"
    }

    # 🔹 Definir el orden de los puestos
    orden_puestos = {"Administrador/a": 1, "ADM": 2, "TS": 3}
    colores_puestos = {
        "Administrador/a": "#9932CC",
        "ADM": "#B0FFB0",
        "TS": "#A3C4FF"
    }

    # 🔹 Obtener todos los usuarios y aplicar orden por puesto
    usuarios = list(users_collection.find({"visible_calendario": {"$ne": False}}))
    usuarios_ordenados = sorted(usuarios, key=lambda u: orden_puestos.get(u.get("puesto", ""), 4))

    # 🔹 Obtener todas las vacaciones registradas
    eventos = list(events_collection.find())

    # Agrupar los eventos por trabajador y por tipo
    eventos_por_trabajador = {}
    for evento in eventos:
        nombre = evento["trabajador"]  # Supongo que se guarda el nombre completo
        tipo = evento.get("tipo", "Vacaciones")
        if nombre not in eventos_por_trabajador:
            eventos_por_trabajador[nombre] = {}
        if tipo not in eventos_por_trabajador[nombre]:
            eventos_por_trabajador[nombre][tipo] = []
        eventos_por_trabajador[nombre][tipo].append((evento["fecha_inicio"], evento["fecha_fin"]))

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

        if fecha_str in festivos:
            eventos_json.append({
                "id": f"Festivo-{fecha_str}",
                "title": "Festivo",
                "start": fecha_str,
                "color": "#A9A9A9",
                "classNames": ["festivo-event"]
            })
            contador_disponibles[fecha_str] = 0

        elif dia_semana < 5:  # Sólo de lunes a viernes
            disponibles_en_dia = 0
            eventos_dia = []

            for usuario in usuarios_ordenados:
                nombre_completo = f"{usuario['nombre']} {usuario['apellidos']}"
                color = colores_puestos.get(usuario["puesto"], "#D3D3D3")
                event_label = f"{usuario['puesto']} - {nombre_completo}"

                # Verifica si hay eventos asignados para este usuario en la fecha
                user_events = eventos_por_trabajador.get(nombre_completo, {})
                evento_asignado = None
                # Verifica en orden de prioridad: Vacaciones, CADE 30, CADE 50, Mail.
                for tipo in ["Baja", "CADE 30", "CADE 50", "CADE Tardes", "Guardia CADE", "Mail", "Vacaciones"]:
                    if tipo in user_events:
                        for inicio, fin in user_events[tipo]:
                            # Suponiendo que inicio y fin son strings "YYYY-MM-DD"
                            if fecha_str >= inicio and fecha_str <= fin:
                                evento_asignado = tipo
                                break
                    if evento_asignado:
                        break
                if evento_asignado:
                    if evento_asignado == "Vacaciones":
                        event_label += " (Ausente)"
                        color = "#E53935"  # Rojo brillante
                    elif evento_asignado == "Baja":
                        event_label += " (Baja)"
                        color = "#757575"  # Gris medio
                    elif evento_asignado == "CADE 30":
                        event_label += " (CADE 30)"
                        color = "#FB8C00"  # Naranja fuerte
                    elif evento_asignado == "CADE 50":
                        event_label += " (CADE 50)"
                        color = "#FDD835"  # Amarillo brillante
                    elif evento_asignado == "CADE Tardes":
                        event_label += " (CADE Tardes)"
                        color = "#F6AE2D"  # Dorado/miel vibrante
                    elif evento_asignado == "Guardia CADE":
                        event_label += " (Guardia CADE)"
                        color = "#49A275"  # Verde oscuro
                    elif evento_asignado == "Mail":
                        event_label += " (Mail)"
                        color = "#8D6E63"  # Marrón rosado apagado
                else:
                    disponibles_en_dia += 1

                eventos_dia.append({
                    "id": f"{nombre_completo}-{fecha_str}",
                    "title": event_label,
                    "start": fecha_str,
                    "color": color
                })

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

@app.route('/admin/asignar-estados', methods=['GET', 'POST'])
@login_required
@admin_required
def asignar_estados():
    if request.method == 'POST':
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')

        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")

        trabajadores = list(users_collection.find())
        
        for trabajador in trabajadores:
            estado = request.form.get(f"tipo_{trabajador['_id']}")
            if not estado:
                continue

            nombre_completo = f"{trabajador['nombre']} {trabajador['apellidos']}"

            # Iterar por cada día del rango
            current_day = fecha_inicio_dt
            while current_day <= fecha_fin_dt:
                day_str = current_day.strftime("%Y-%m-%d")

                query_filter = {
                    "trabajador": nombre_completo,
                    "fecha_inicio": day_str,
                    "fecha_fin": day_str,
                    "tipo": {"$in": ["Baja", "CADE 30", "CADE 50", "CADE Tardes", "Guardia CADE", "Mail"]}
                }

                if estado == "normal":
                    # Intentamos eliminar los eventos especiales para este trabajador y este rango
                    events_collection.delete_many(query_filter)
                else:
                    # Primero eliminamos cualquier evento previo especial en ese rango (para evitar duplicados)
                    events_collection.delete_many(query_filter)
                    # Luego insertamos el nuevo evento
                    nuevo_evento = {
                        "trabajador": nombre_completo,
                        "fecha_inicio": day_str,
                        "fecha_fin": day_str,
                        "tipo": estado
                    }
                    events_collection.insert_one(nuevo_evento)
                    
                current_day += timedelta(days=1)
            
        return redirect(url_for('asignar_estados'))
    else:
        trabajadores = list(users_collection.find())
        trabajadores = sorted(trabajadores, key=lambda x: (x['nombre'].lower(), x['apellidos'].lower()))
        return render_template("asignar_estados.html", trabajadores=trabajadores)

@app.route('/admin/duplicados', methods=['GET'])
@login_required
@admin_required
def duplicados():
    pipeline = [
        {
            "$group": {
                "_id": {
                    "trabajador": "$trabajador",
                    "fecha_inicio": "$fecha_inicio",
                    "fecha_fin": "$fecha_fin"
                },
                "tipos": {"$addToSet": "$tipo"},
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"}
            }
        },
        {
            "$match": {
                "$expr": {"$gt": [{"$size": "$tipos"}, 1]}
            }
        },
        {
            "$sort": {"_id.fecha_inicio": 1}
        }
    ]
    duplicados = list(events_collection.aggregate(pipeline))
    return render_template("duplicados.html", duplicados=duplicados)

# Configuramos asistente de IA

import openai
import pinecone
from pinecone import Pinecone
from openai import OpenAI
from procesar_pdfs import guardar_pdf_en_pinecone, extraer_texto_pdf


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# 🔹 Configurar Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
# Inicializar Pinecone correctamente con la nueva sintaxis
pc = Pinecone(api_key=PINECONE_API_KEY)

# 🔹 Inicializar cliente de OpenAI
client = OpenAI()

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Verificar si el índice existe antes de usarlo
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    print(f"❌ El índice '{PINECONE_INDEX_NAME}' no existe en Pinecone.")
else:
    index = pc.Index(PINECONE_INDEX_NAME)


@app.route('/ai-response', methods=['POST'])
@login_required
def ai_response():
    data = request.get_json()
    user_message = data.get("message")  # Extraer el mensaje del usuario

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # 🔹 Obtener los resultados de Pinecone (lista de tuplas: (texto, documento, página))
    resultados = buscar_en_pinecone(user_message)

    # Separar el texto relevante de cada fragmento
    context_texts = [r[0] for r in resultados]
    contexto_str = "\n".join(context_texts) if context_texts else "No se encontró información relevante."

    # Construir la lista de fuentes, incluyendo el documento y la página
    # Se crea un set para evitar duplicados
    fuentes_set = {(r[1], r[2]) for r in resultados if r[1] != "Desconocido"}
    doc_str = ", ".join([f"{name} (página {page})" for name, page in fuentes_set]) if fuentes_set else "No se encontraron documentos relevantes."

    # 🔹 Recuperar el historial de conversación (últimos N mensajes) si lo usas
    historial = list(historial_collection.find({"usuario": current_user.usuario}).sort("timestamp", -1).limit(5))
    historial_str = "\n".join([f"Usuario: {h['mensaje']}\nAsistente: {h['respuesta']}" for h in historial])

    # 🔹 Generar respuesta con OpenAI
    prompt = f"""
    Contexto relevante recuperado:
    {contexto_str}

    Historial de conversación:
    {historial_str}

    Usuario: {user_message}
    Asistente:
    """

    response = client.chat.completions.create(
        model="o3-mini",
        messages=[
            {"role": "system", "content": "Actúa como un asistente experto en la gestión de expedientes de dependencia que ayuda a los trabajadores de la sección PIAS del Instituto Aragonés de Servicios Sociales (IASS) a buscar información. Tu ámbito de conocimiento se centra exclusivamente en los procesos y la herramienta informática utilizada en esta sección. Cuando un trabajador te consulte, responde de forma concisa y directa a su pregunta, proporcionando la información o la guía necesaria para resolver su duda o avanzar en el proceso. Prioriza la claridad y la utilidad práctica en tus respuestas. Evita dar información que no esté directamente relacionada con la gestión de expedientes de dependencia en la herramienta informática del IASS. Recuerda que tu objetivo principal es ser una herramienta de apoyo eficaz y eficiente para los empleados."},
            {"role": "user", "content": prompt}
        ]
    )

    respuesta_final = response.choices[0].message.content

    # 🔹 Guardar en MongoDB el historial de conversación
    guardar_historial(current_user.usuario, user_message, respuesta_final)

    # Enviar también las fuentes (doc_str) en la respuesta
    return jsonify({
        "response": respuesta_final,
        "sources": doc_str
    })



def guardar_texto_en_pinecone(texto, metadata={}):
    """Convierte un texto en embeddings y lo almacena en Pinecone."""
    
    # 🔹 Generar embeddings con OpenAI
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=[texto]  # Debe ser una lista
    )
    
    embedding = response["data"][0]["embedding"]

    # 🔹 Guardar en Pinecone
    id_vector = str(uuid.uuid4())  # Generar un ID único para el vector
    index.upsert([(id_vector, embedding, metadata)])
    
    return id_vector

def buscar_en_pinecone(texto, documento=None):
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=texto
    )
    embedding = response.data[0].embedding

    filtro = {"documento": {"$eq": documento}} if documento else {}

    resultados = index.query(vector=embedding, top_k=5, include_metadata=True, filter=filtro)

    # Devolver una lista de tuplas (texto_del_fragmento, nombre_del_documento, pagina)
    return [
        (
            res["metadata"].get("texto", ""),
            res["metadata"].get("documento", "Desconocido"),
            res["metadata"].get("pagina", "N/D")
        )
        for res in resultados.get("matches", [])
    ]

def guardar_historial(usuario, mensaje, respuesta):
    """Guarda una conversación en MongoDB."""
    historial_collection.insert_one({
        "usuario": usuario,
        "mensaje": mensaje,
        "respuesta": respuesta,
        "timestamp": datetime.now(timezone.utc)
    })

"""@app.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def upload_pdf():
    if request.method == "POST":
        if "file" not in request.files:
            return "❌ No se subió ningún archivo", 400
        
        file = request.files["file"]
        if file.filename == "":
            return "❌ No se seleccionó ningún archivo", 400

        # 🔹 Guardar archivo en la carpeta 'uploads'
        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(pdf_path)

        # 🔹 Procesar el PDF y guardarlo en Pinecone
        resultado = guardar_pdf_en_pinecone(pdf_path)
        
        return jsonify({"message": resultado})

    return render_template("upload.html")  # Página para subir archivos
    """

"""@app.route("/search", methods=["GET", "POST"])
def search():
    documentos = index.describe_index_stats()["namespaces"].keys()  # 🔹 Obtener documentos en Pinecone
    resultados = []

    if request.method == "POST":
        query = request.form.get("query")
        documento = request.form.get("documento") or None  # None significa "todos los documentos"

        resultados = buscar_en_pinecone(query, documento)

    return render_template("search.html", documentos=documentos, resultados=resultados)

"""

# 🔹 Ruta para subir archivos desde la web
"""@app.route("/subir-pdf", methods=["GET", "POST"])
@login_required
@admin_required
def subir_pdf():
    if request.method == "POST":
        if "archivo" not in request.files:
            return jsonify({"error": "No se ha seleccionado ningún archivo."}), 400

        archivo = request.files["archivo"]

        if archivo.filename == "":
            return jsonify({"error": "El archivo no tiene nombre válido."}), 400

        if archivo and archivo.filename.endswith(".pdf"):
            archivo_path = os.path.join(app.config["UPLOAD_FOLDER"], archivo.filename)
            archivo.save(archivo_path)

            # Guardar el PDF en Pinecone
            resultado = guardar_pdf_en_pinecone(archivo_path, archivo.filename)
            
            # Opcional: puedes almacenar un mensaje de éxito en flash para mostrarlo en el dashboard
            from flask import flash
            flash(resultado)
            
            return redirect(url_for('dashboard'))

        return jsonify({"error": "Formato no válido. Solo se permiten archivos PDF."}), 400

    return render_template("subir_pdf.html")
"""
import os
import re

def custom_filename(filename):
    """
    Limpia el nombre del archivo permitiendo espacios, puntos y guiones.
    Elimina caracteres no deseados, pero conserva los espacios.
    """
    filename = os.path.basename(filename)
    # Permite letras, dígitos, espacios, guiones y puntos.
    filename = re.sub(r'[^\w\s\.-]', '', filename)
    # Reemplaza múltiples espacios por uno solo y quita espacios al inicio/final.
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

@app.route("/subir-pdf", methods=["GET", "POST"])
@login_required
@admin_required
def subir_pdf():
    if request.method == "POST":
        if "archivo" not in request.files:
            return jsonify({"error": "No se ha seleccionado ningún archivo."}), 400

        archivo = request.files["archivo"]
        if archivo.filename == "":
            return jsonify({"error": "El archivo no tiene nombre válido."}), 400

        if archivo and archivo.filename.lower().endswith(".pdf"):
            # Usa la función personalizada para normalizar el nombre y conservar espacios.
            filename = custom_filename(archivo.filename)
            temp_path = os.path.join("uploads", filename)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            # Guarda el archivo temporalmente usando un bloque with para asegurarte de cerrarlo.
            with open(temp_path, 'wb') as f:
                f.write(archivo.read())
            
            try:
                # Sube el archivo a S3.
                s3_client.upload_file(
                    temp_path,
                    os.environ.get("AWS_S3_BUCKET"),
                    f"uploads/{filename}",
                    ExtraArgs={"ContentType": archivo.content_type}
                )
                file_url = f"https://{os.environ.get('AWS_S3_BUCKET')}.s3.{os.environ.get('AWS_S3_REGION')}.amazonaws.com/uploads/{filename}"
                
                # Procesa el PDF y almacena en Pinecone.
                resultado = guardar_pdf_en_pinecone(temp_path, filename, index)
        
                
                return redirect(url_for('dashboard'))
            except Exception as e:
                print("Error al subir a S3 o procesar en Pinecone:", e, flush=True)
                return jsonify({"error": "Error al subir el archivo."}), 500

        return jsonify({"error": "Formato no válido. Solo se permiten archivos PDF."}), 400

    return render_template("subir_pdf.html")


@app.route("/documentos_subidos_s3", methods=["GET"])
@login_required  # O el nivel de restricción que prefieras
def documentos_subidos_s3():
    try:
        response = s3_client.list_objects_v2(
            Bucket=AWS_S3_BUCKET,
            Prefix="uploads/"
        )
        # response.get("Contents") es una lista de objetos
        files = []
        for obj in response.get("Contents", []):
            # Extraemos el nombre del archivo
            key = obj["Key"]
            # Construimos la URL del archivo
            file_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{key}"
            files.append({"name": key.split("/")[-1], "url": file_url})
    except Exception as e:
        print("Error al listar archivos en S3:", e)
        files = []
    
    return render_template("documentos_subidos.html", files=files)

@app.route("/eliminar_documento", methods=["POST"])
@login_required
@admin_required
def eliminar_documento():
    filename = request.form.get("filename")
    
    if not filename:
        flash("No se especificó ningún archivo para eliminar", "error")
        return redirect(url_for("documentos_subidos_s3"))
    
    try:
        # 1. Eliminar el archivo de S3
        s3_object_key = f"uploads/{filename}"
        s3_client.delete_object(
            Bucket=AWS_S3_BUCKET,
            Key=s3_object_key
        )
        
        # 2. Eliminar los vectores asociados de Pinecone
        try:
            # Obtener todos los vectores con el mismo nombre de documento
            fetch_response = index.query(
                vector=[0] * 1536,  # Vector de ceros de la dimensión correcta
                filter={"documento": {"$eq": filename}},
                top_k=10000,  # Aumentar para manejar más vectores
                include_metadata=True
            )
            
            matches = fetch_response.matches
            if matches:
                ids_to_delete = [match.id for match in matches]
                # Eliminar en lotes de 1000 para evitar límites potenciales
                for i in range(0, len(ids_to_delete), 1000):
                    batch = ids_to_delete[i:i + 1000]
                    index.delete(ids=batch)
                print(f"Se eliminaron {len(ids_to_delete)} vectores de Pinecone para '{filename}'")
            else:
                print(f"No se encontraron vectores en Pinecone para '{filename}'")
                
        except Exception as e:
            print(f"Error al eliminar vectores de Pinecone: {str(e)}")
            flash(f"Archivo eliminado de S3, pero hubo un error al eliminar de Pinecone: {str(e)}", "warning")
            return redirect(url_for("documentos_subidos_s3"))
        
        flash(f"El documento '{filename}' ha sido eliminado correctamente de S3 y Pinecone", "success")
        return redirect(url_for("documentos_subidos_s3"))
        
    except Exception as e:
        flash(f"Error al eliminar el documento: {str(e)}", "error")
        return redirect(url_for("documentos_subidos_s3"))
    

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False, use_debugger=False)
