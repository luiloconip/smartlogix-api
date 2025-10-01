# main.py
import os
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text

app = Flask(__name__)

# Configuración de la base de datos desde variables de entorno
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "smartlogix_academy")
CLOUD_SQL_CONNECTION_NAME = os.environ.get("CLOUD_SQL_CONNECTION_NAME", "")

# Construir la URL de conexión para PostgreSQL en Cloud SQL (usando socket Unix)
if os.getenv("GAE_ENV", "").startswith("standard"):
    # Entorno App Engine (no es nuestro caso, pero por seguridad)
    host_args = f"host=/cloudsql/{CLOUD_SQL_CONNECTION_NAME}"
else:
    # Entorno Cloud Run
    host_args = f"host=/cloudsql/{CLOUD_SQL_CONNECTION_NAME}"

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?{host_args}"

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)

# Ruta: Registrar estudiante
@app.route('/students', methods=['POST'])
def create_student():
    data = request.get_json()
    if not data or 'nombre' not in data or 'correo' not in data:
        return jsonify({"error": "Faltan campos: nombre y correo"}), 400

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO students (nombre, correo)
                    VALUES (:nombre, :correo)
                    RETURNING id
                """),
                {"nombre": data["nombre"], "correo": data["correo"]}
            )
            student_id = result.fetchone()[0]
        return jsonify({"id": student_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta: Registrar curso
@app.route('/courses', methods=['POST'])
def create_course():
    data = request.get_json()
    if not data or 'titulo' not in data:
        return jsonify({"error": "Falta el campo: titulo"}), 400

    descripcion = data.get("descripcion", "")
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO courses (titulo, descripcion)
                    VALUES (:titulo, :descripcion)
                    RETURNING id
                """),
                {"titulo": data["titulo"], "descripcion": descripcion}
            )
            course_id = result.fetchone()[0]
        return jsonify({"id": course_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta: Matricular estudiante en curso
@app.route('/enrollments', methods=['POST'])
def enroll_student():
    data = request.get_json()
    if not data or 'student_id' not in data or 'course_id' not in data:
        return jsonify({"error": "Faltan: student_id y course_id"}), 400

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO enrollments (student_id, course_id, estado, puntaje)
                    VALUES (:student_id, :course_id, 'Activo', 100)
                    RETURNING id
                """),
                {"student_id": data["student_id"], "course_id": data["course_id"]}
            )
            enrollment_id = result.fetchone()[0]
        return jsonify({"id": enrollment_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta: Cambiar estado de matrícula (ej. a "Inactivo")
@app.route('/enrollments/<int:id>', methods=['PUT'])
def update_enrollment(id):
    data = request.get_json()
    nuevo_estado = data.get("estado", "Inactivo")  # Por defecto "Inactivo"

    if nuevo_estado not in ["Activo", "Inactivo"]:
        return jsonify({"error": "Estado debe ser 'Activo' o 'Inactivo'"}), 400

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("UPDATE enrollments SET estado = :estado WHERE id = :id"),
                {"estado": nuevo_estado, "id": id}
            )
            if result.rowcount == 0:
                return jsonify({"error": "Matrícula no encontrada"}), 404
        return jsonify({"message": "Estado actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta: Listar cursos de un estudiante
@app.route('/students/<int:student_id>/enrollments', methods=['GET'])
def get_student_enrollments(student_id):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT c.titulo, e.estado, e.puntaje, e.fecha_matricula
                    FROM enrollments e
                    JOIN courses c ON e.course_id = c.id
                    WHERE e.student_id = :student_id
                """),
                {"student_id": student_id}
            )
            rows = result.fetchall()

        if not rows:
            return jsonify([]), 200

        enrollments = []
        for row in rows:
            enrollments.append({
                "curso": row[0],
                "estado": row[1],
                "puntaje": row[2],
                "fecha_matricula": row[3].isoformat() if row[3] else None
            })

        return jsonify(enrollments), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ruta de salud (opcional, útil para Cloud Run)
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))