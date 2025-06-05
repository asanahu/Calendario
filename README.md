Calendario+ Asistente de IA

Calendario+ Asistente de IA es una aplicación web desarrollada en Flask que integra múltiples funcionalidades para la gestión de empleados en entornos empresariales. El proyecto permite gestionar vacaciones, asignar estados especiales (como CADE 30, CADE 50, Mail, Baja), y ofrece un asistente virtual que utiliza modelos de lenguaje (OpenAI) para proporcionar respuestas contextualizadas basadas en información de la empresa.

Funcionalidades Principales

Calendario Interactivo:
Visualiza un calendario con los eventos de los empleados. Utiliza FullCalendar para mostrar los días, con botones de navegación en el header y footer para cambiar de mes, semana o día.

Los empleados se muestran con colores según su puesto (por ejemplo, azul para TS y verde para Administradores).
Los eventos especiales (Vacaciones, CADE 30, CADE 50, Mail, Baja) se distinguen con colores personalizados.

Gestión de Eventos:
La aplicación permite registrar eventos en la colección de MongoDB, donde se almacena el nombre del trabajador, el rango de fechas y el tipo de evento.

Se pueden asignar estados especiales por parte de los administradores.
Se evita la duplicidad de eventos al actualizar o eliminar eventos que se solapan.

Panel de Administración para Asignar Estados:
Un formulario dedicado permite a los administradores asignar estados semanales a los empleados.

Los estados disponibles incluyen: "Baja", "CADE 30", "CADE 50", "Mail" y "Normal" (para restaurar el estado estándar).
La interfaz se organiza en múltiples columnas para una visualización ágil de los trabajadores.

Asistente Virtual (IA):
Integra un asistente de IA que utiliza el modelo GPT-4 Mini (u otros modelos de OpenAI) para responder a preguntas de los empleados basándose en:

El historial de conversaciones.
Información extraída de documentos PDF procesados y almacenados en Pinecone.

Gestión de Documentos:
Permite subir documentos PDF (por ejemplo, manuales o informes) que se almacenan en Amazon S3.

Se extrae el contenido del PDF y se guarda en Pinecone para búsquedas semánticas.
Se proporciona una vista para que los administradores consulten el repositorio documental.

Autenticación y Gestión de Usuarios:
Los usuarios deben iniciar sesión mediante usuario y contraseña.

Las contraseñas se almacenan de forma segura utilizando hash (con Werkzeug).
La autenticación se gestiona con Flask-Login.

Tecnologías Utilizadas
Backend: Flask, Flask-Login, PyMongo
Frontend: HTML, CSS, JavaScript, FullCalendar
Base de Datos: MongoDB
Almacenamiento de Archivos: Amazon S3
Vector Storage & Búsqueda Semántica: Pinecone
Asistente de IA: OpenAI (GPT-4 Mini)
Gestión de Variables de Entorno: python-dotenv

Configuración
Para ejecutar el proyecto, asegúrate de definir las siguientes variables de entorno en un archivo .env:

MONGO_URI: URI de conexión a MongoDB.
SECRET_KEY: Clave secreta para Flask.
AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY: Credenciales de AWS.
AWS_S3_BUCKET: Nombre del bucket en S3.
AWS_S3_REGION: Región de S3.
OPENAI_API_KEY: Clave API de OpenAI.
PINECONE_API_KEY: Clave API de Pinecone.
PINECONE_ENVIRONMENT: Entorno de Pinecone.
PINECONE_INDEX_NAME: Nombre del índice en Pinecone.


Instalación y Ejecución
- Clona el repositorio
- Crea un entorno virtual e instala las dependencias
pip install -r requirements.txt
- Configura las variables de entorno en un archivo .env.

- Ejecuta la aplicación:

python app.py

Uso
Dashboard:
Después del login, los usuarios son redirigidos a un dashboard con botones para acceder al calendario, asistente de IA, panel de administración y repositorio documental.

Administración:
Los administradores pueden:

Subir documentos.
Asignar estados a los empleados mediante la interfaz de asignación de estados.
Consultar y gestionar usuarios y eventos.
Calendario y Asistente de IA:
Los empleados pueden consultar su calendario y usar el asistente de IA para resolver dudas sobre procesos y la herramienta interna.

Registro de turnos recurrentes:
Es posible registrar eventos periódicos visitando la ruta `/add-recurring`. Solo hay que indicar la fecha de inicio, la fecha de fin y la frecuencia (semanal o cada cierto número de días) junto con los días de la semana deseados. La aplicación generará automáticamente un evento por cada día resultante.

Contribuciones
¡Las contribuciones son bienvenidas! Si deseas colaborar o mejorar el proyecto, por favor crea un fork y envía un pull request.
