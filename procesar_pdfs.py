from flask import Flask, request, render_template, redirect, url_for, jsonify
import fitz  # pymupdf
from pinecone import Pinecone, ServerlessSpec
import openai
import os
import uuid
from dotenv import load_dotenv
import time
import uuid
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
    import fitz  # pymupdf
    doc = fitz.open(pdf_path)
    fragmentos_con_paginas = []
    for num_pagina, pagina in enumerate(doc, start=1):
        texto_pagina = pagina.get_text("text")
        palabras = texto_pagina.split()
        fragmentos = [" ".join(palabras[i:i+500]) for i in range(0, len(palabras), 500)]
        for frag in fragmentos:
            if frag.strip():
                fragmentos_con_paginas.append((frag, num_pagina))
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

def guardar_pdf_en_pinecone(pdf_path, doc_name, index):
    try:
        # First, get all vectors with matching document name
        fetch_response = index.query(
            vector=[0] * 1536,  # Use a zero vector of correct dimension
            filter={"documento": {"$eq": doc_name}},
            top_k=10000,  # Increase to handle more vectors
            include_metadata=True,
            namespace=""
        )
        
        matches = fetch_response.matches
        if matches:
            ids_to_delete = [match.id for match in matches]
            # Delete in batches of 1000 to avoid potential limits
            for i in range(0, len(ids_to_delete), 1000):
                batch = ids_to_delete[i:i + 1000]
                index.delete(ids=batch, namespace="")
        else:
            print(f"No se encontraron vectores existentes para '{doc_name}'", flush=True)

    except Exception as e:
        print(f"Error al eliminar vectores previos: {str(e)}", flush=True)
        
    # Continue with the rest of your existing code...
    fragmentos_con_paginas = extraer_texto_pdf(pdf_path)
    if not fragmentos_con_paginas:
        return f"❌ No se pudo procesar '{doc_name}'"

    vectors_to_upsert = []
    for frag, num_pagina in fragmentos_con_paginas:
        try:
            embedding_response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=frag
            )
            embedding = embedding_response.data[0].embedding
            vector_id = str(uuid.uuid4())
            metadata = {"texto": frag, "documento": doc_name, "pagina": num_pagina}
            vectors_to_upsert.append((vector_id, embedding, metadata))
            
            # Upsert in batches of 100
            if len(vectors_to_upsert) >= 100:
                index.upsert(vectors=vectors_to_upsert, namespace="")
                vectors_to_upsert = []
                
        except Exception as e:
            print(f"❌ Error al procesar fragmento: {str(e)}", flush=True)
            return f"❌ No se pudo procesar '{doc_name}'"

    # Upsert any remaining vectors
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert, namespace="")

    return f"✅ PDF '{doc_name}' procesado y almacenado en Pinecone"


if __name__ == "__main__":
    app.run(debug=True)
