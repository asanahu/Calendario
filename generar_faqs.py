from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import hdbscan
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime
import numpy as np
import json
import os
import sys

# === CARGAR VARIABLES DE ENTORNO ===
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB")
COLLECTION_NAME = "historial_conversaciones"
N_FAQS_MIN_PREGUNTAS = 3
FECHA_MINIMA = datetime(2025, 5, 1)

# Añadir fecha de origen en formato español
# fecha_origen_es = FECHA_MINIMA.strftime("%-d de %B de %Y")  # Linux/macOS
fecha_origen_es = FECHA_MINIMA.strftime("%#d de %B de %Y")  # Windows

# === CONECTAR A MONGO ===
client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

# === CARGAR DATOS CON FILTRO POR FECHA ===
print(f"🔍 Extrayendo preguntas/respuestas desde el {FECHA_MINIMA.date()}...")
documentos = list(collection.find({
    "mensaje": {"$exists": True},
    "respuesta": {"$exists": True},
    "timestamp": {"$gte": FECHA_MINIMA}
}))
print(f"📦 Total documentos encontrados: {len(documentos)}")

# Mostrar muestra para confirmar formato
for doc in documentos[:3]:
    print("Ejemplo:", doc)

if len(documentos) == 0:
    print("❌ No se encontraron documentos con los campos 'mensaje' y 'respuesta' después de la fecha indicada.")
    sys.exit(1)

# === EXTRAER PREGUNTAS Y RESPUESTAS ===
preguntas = [d["mensaje"] for d in documentos]
respuestas = [d["respuesta"] for d in documentos]

# === EMBEDDINGS ===
print("📐 Generando embeddings...")
modelo = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = modelo.encode(preguntas, show_progress_bar=True)

if len(embeddings) == 0:
    print("❌ No se pudieron generar embeddings. ¿Lista vacía?")
    sys.exit(1)

# === CLUSTERING ===
print("🧠 Aplicando HDBSCAN para agrupar preguntas similares...")
clusterer = hdbscan.HDBSCAN(min_cluster_size=3, metric='euclidean')
labels = clusterer.fit_predict(embeddings)

# === AGRUPAR POR CLUSTER ===
faq_dict = defaultdict(list)
for idx, label in enumerate(labels):
    if label != -1:
        faq_dict[label].append({
            "pregunta": preguntas[idx],
            "respuesta": respuestas[idx],
            "embedding": embeddings[idx]
        })

# === SELECCIONAR REPRESENTANTE POR GRUPO ===
faqs = []
for grupo in faq_dict.values():
    if len(grupo) >= N_FAQS_MIN_PREGUNTAS:
        centroide = np.mean([p["embedding"] for p in grupo], axis=0)
        similitudes = [cosine_similarity([p["embedding"]], [centroide])[0][0] for p in grupo]
        idx_max = np.argmax(similitudes)
        representativa = grupo[idx_max]
        faqs.append({
            "pregunta": representativa["pregunta"],
            "respuesta": representativa["respuesta"],
            "frecuencia": len(grupo)
        })

# === GUARDAR RESULTADO ===
print(f"💾 Guardando {len(faqs)} FAQs generadas en faqs_generadas.json...")
resultado = {
    "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "fecha_origen": fecha_origen_es,
    "faqs": faqs
}

with open("faqs_generadas.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, indent=2, ensure_ascii=False)

print("✅ Proceso completado.")
