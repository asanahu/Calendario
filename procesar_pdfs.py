from flask import Flask, request, render_template, redirect, url_for, jsonify
import fitz  # pymupdf
from pinecone import Pinecone, ServerlessSpec
import openai
import os
import uuid
from dotenv import load_dotenv

# 🔹 Cargar variables de entorno
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🔹 Verificar credenciales antes de continuar
if not PINECONE_API_KEY or not PINECONE_INDEX_NAME or not OPENAI_API_KEY:
    raise ValueError("❌ Falta una clave de API. Verifica las variables de entorno.")

# 🔹 Inicializar Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# 🔹 Verificar si el índice existe, y si no, crearlo
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    print(f"⚠️ El índice '{PINECONE_INDEX_NAME}' no existe. Creándolo...")
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-west-2")
    )
    print(f"✅ Índice '{PINECONE_INDEX_NAME}' creado con éxito.")

# 🔹 Conectar al índice
index = pc.Index(PINECONE_INDEX_NAME)

# 🔹 Configurar Flask
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extraer_texto_pdf(pdf_path):
    """Extrae el texto de un PDF y lo divide en fragmentos de 500 palabras."""
    doc = fitz.open(pdf_path)
    texto_completo = ""

    for pagina in doc:
        texto_completo += pagina.get_text("text") + "\n"

    # 🔹 Dividir el texto en fragmentos de 500 palabras
    palabras = texto_completo.split()
    fragmentos = [" ".join(palabras[i:i+500]) for i in range(0, len(palabras), 500)]

    return fragmentos


def guardar_pdf_en_pinecone(pdf_path, doc_name):
    """Procesa un PDF, genera embeddings y los guarda en Pinecone."""
    fragmentos = extraer_texto_pdf(pdf_path)

    if not fragmentos:
        print(f"⚠️ No se encontró texto en el archivo '{doc_name}'.")
        return f"❌ No se pudo procesar '{doc_name}'"

    for fragmento in fragmentos:
        try:
            # 🔹 Generar embedding con OpenAI usando la nueva sintaxis
            embedding_response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=fragmento
            )
            embedding = embedding_response.data[0].embedding  # ✅ Nueva forma de acceder al embedding

            # 🔹 Guardar en Pinecone con un ID único
            id_vector = str(uuid.uuid4())
            index.upsert([(id_vector, embedding, {"texto": fragmento, "documento": doc_name})])

        except Exception as e:
            print(f"❌ Error al procesar '{doc_name}': {e}")
            return f"❌ No se pudo procesar '{doc_name}'"

    return f"✅ PDF '{doc_name}' procesado y almacenado en Pinecone."

if __name__ == "__main__":
    app.run(debug=True)
