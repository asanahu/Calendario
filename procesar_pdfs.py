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


"""def extraer_texto_pdf(pdf_path):
"""
"""
    Extrae el texto de un PDF y lo divide en fragmentos de 500 palabras,
    devolviendo una lista de tuplas: (fragmento, número_de_página)"""
"""
    doc = fitz.open(pdf_path)
    fragmentos_con_paginas = []

    # Recorre cada página, empezando en 1
    for num_pagina, pagina in enumerate(doc, start=1):
        texto_pagina = pagina.get_text("text")
        palabras = texto_pagina.split()
        # Dividir el texto de la página en fragmentos de 500 palabras
        fragmentos = [" ".join(palabras[i:i+500]) for i in range(0, len(palabras), 500)]
        for fragmento in fragmentos:
            if fragmento.strip():  # Evita fragmentos vacíos
                fragmentos_con_paginas.append((fragmento, num_pagina))
    
    return fragmentos_con_paginas"""

def extraer_texto_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    fragmentos_con_paginas = []
    for num_pagina, pagina in enumerate(doc, start=1):
        texto_pagina = pagina.get_text("text")
        palabras = texto_pagina.split()
        fragmentos = [" ".join(palabras[i:i+500]) for i in range(0, len(palabras), 500)]
        for fragmento in fragmentos:
            if fragmento.strip():
                fragmentos_con_paginas.append((fragmento, num_pagina))
    return fragmentos_con_paginas

"""
def guardar_pdf_en_pinecone(pdf_path, doc_name):
"""
"""  Procesa un PDF, genera embeddings y los guarda en Pinecone,
    eliminando primero los vectores previos asociados al mismo nombre de documento.
    Cada fragmento se almacena junto con su número de página."""
"""
    # Eliminar vectores previos que tengan el mismo nombre de documento.
    try:
        index.delete(filter={"documento": {"$eq": doc_name}})
        print(f"Vectores para '{doc_name}' eliminados (si existían).")
    except Exception as e:
        print("Error al eliminar vectores previos:", e)
    
    # Extraer el texto y obtener fragmentos junto con el número de página.
    fragmentos_con_paginas = extraer_texto_pdf(pdf_path)

    if not fragmentos_con_paginas:
        print(f"⚠️ No se encontró texto en el archivo '{doc_name}'.")
        return f"❌ No se pudo procesar '{doc_name}'"

    for fragmento, num_pagina in fragmentos_con_paginas:
        try:
            # Generar el embedding para el fragmento.
            embedding_response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=fragmento
            )
            embedding = embedding_response.data[0].embedding

            # Generar un ID único para el vector.
            id_vector = str(uuid.uuid4())
            metadata = {"texto": fragmento, "documento": doc_name, "pagina": num_pagina}
            print("Subiendo vector con metadata:", metadata)  # Debug
            # Insertar en Pinecone con metadata que incluye el nombre del documento y la página.
            index.upsert([(
                id_vector,
                embedding,
                metadata
            )])
        except Exception as e:
            print(f"❌ Error al procesar '{doc_name}': {e}")
            return f"❌ No se pudo procesar '{doc_name}'"

    return f"✅ PDF '{doc_name}' procesado y almacenado en Pinecone."

"""

def guardar_pdf_en_pinecone(pdf_path, doc_name):
    try:
        index.delete(filter={"documento": {"$eq": doc_name}})
    except Exception as e:
        print("Error al eliminar vectores previos:", e, flush=True)
    
    fragmentos_con_paginas = extraer_texto_pdf(pdf_path)
    
    if not fragmentos_con_paginas:
        print(f"⚠️ No se encontró texto en el archivo '{doc_name}'.", flush=True)
        return f"❌ No se pudo procesar '{doc_name}'"
    
    for fragmento, num_pagina in fragmentos_con_paginas:
        try:
            embedding_response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=fragmento
            )
            embedding = embedding_response.data[0].embedding
            id_vector = str(uuid.uuid4())
            metadata = {"texto": fragmento, "documento": doc_name, "pagina": num_pagina}
            index.upsert([(
                id_vector,
                embedding,
                metadata
            )])
        except Exception as e:
            print(f"❌ Error al procesar '{doc_name}':", e, flush=True)
            return f"❌ No se pudo procesar '{doc_name}'"
    
    return f"✅ PDF '{doc_name}' procesado y almacenado en Pinecone."

if __name__ == "__main__":
    app.run(debug=True)
