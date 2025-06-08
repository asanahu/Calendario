📅 Calendario+ Asistente de IA
Calendario+ es una aplicación web desarrollada en Flask para gestionar eventos y asistencia de empleados en entornos empresariales. Integra funciones avanzadas como un calendario interactivo, panel de administración, métricas de disponibilidad y un asistente virtual basado en IA que ofrece respuestas personalizadas a partir de datos de la organización.

🚀 Funcionalidades Principales
🗓️ Calendario Interactivo
Visualización de eventos por empleado con FullCalendar.

Navegación por día, semana o mes.

Colores personalizados según el puesto del trabajador y el tipo de evento:

Ej.: Azul para TS, Verde para Administradores, colores diferenciados para Vacaciones, CADE 30, CADE 50, Mail, Baja…

✏️ Gestión de Eventos
Creación, edición y eliminación de eventos guardados en MongoDB.

Prevención de duplicidades y solapamientos de fechas.

Registro de eventos recurrentes a través de /add-recurring.

🛠️ Panel de Administración
Interfaz de múltiples columnas para una asignación rápida de estados.

Estados disponibles: Normal, Baja, CADE 30, CADE 50, Mail.

🤖 Asistente Virtual IA
Asistente con GPT-4 (OpenAI).

Ofrece respuestas contextualizadas a partir de:

Historial de conversaciones.

Documentación cargada y procesada semánticamente con Pinecone.

📄 Gestión Documental
Subida de documentos PDF a Amazon S3.

Extracción automática de contenido para búsquedas semánticas.

Interfaz de consulta documental accesible por los administradores.

🔐 Autenticación y Gestión de Usuarios
Login protegido con Flask-Login.

Contraseñas encriptadas con Werkzeug.

Roles diferenciados: usuario estándar vs administrador.

📊 Métricas de Disponibilidad
Tablas y gráficos accesibles desde /dashboard-metrics.

Filtrado por fechas.

Exclusión automática de fines de semana y festivos en el conteo.

🧰 Tecnologías Utilizadas
Componente	Tecnología
Backend	Flask, PyMongo, Flask-Login
Frontend	HTML, CSS, JavaScript, FullCalendar
Base de Datos	MongoDB
Almacenamiento	Amazon S3
IA & NLP	OpenAI GPT-4 Mini, Pinecone
Entorno	python-dotenv

⚙️ Configuración
Crea un archivo .env con las siguientes variables:

dotenv
Copiar
Editar
MONGO_URI=<tu_uri_mongodb>
SECRET_KEY=<tu_clave_secreta>
AWS_ACCESS_KEY_ID=<tu_clave_aws>
AWS_SECRET_ACCESS_KEY=<tu_secreto_aws>
AWS_S3_BUCKET=<nombre_bucket>
AWS_S3_REGION=<region_bucket>
OPENAI_API_KEY=<clave_openai>
PINECONE_API_KEY=<clave_pinecone>
PINECONE_ENVIRONMENT=<entorno_pinecone>
PINECONE_INDEX_NAME=<indice_pinecone>
🧪 Instalación y Ejecución
bash
Copiar
Editar
# 1. Clonar el repositorio
git clone https://github.com/tu_usuario/calendario-ai.git
cd calendario-ai

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/bin/activate  # en Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Ejecutar la aplicación
python app.py
🧭 Navegación Principal
/login: acceso seguro para usuarios registrados.

/dashboard: panel principal con accesos al calendario, métricas, IA y gestión.

/admin: panel exclusivo para administradores.

/add-recurring: creación de eventos periódicos.

/dashboard-metrics: análisis visual por trabajador y período.

🤝 Contribuciones
¡Las contribuciones son bienvenidas!
Puedes abrir un Issue o enviar un Pull Request para proponer mejoras, nuevas funciones o correcciones de errores.
