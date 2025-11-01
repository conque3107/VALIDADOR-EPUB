from flask import Flask, request, jsonify
import subprocess
import os
import tempfile
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuración
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'epub'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return jsonify({
        "status": "ok",
        "message": "EPUB Validator API",
        "endpoints": {
            "/validate": "POST - Upload EPUB file for validation"
        }
    })

@app.route('/validate', methods=['POST'])
def validate_epub():
    # Verificar que hay un archivo
    if 'file' not in request.files:
        return jsonify({
            "valid": False,
            "error": "No file provided",
            "errors": ["No se proporcionó ningún archivo"],
            "warnings": [],
            "version": "N/A"
        }), 400
    
    file = request.files['file']
    
    # Verificar nombre de archivo
    if file.filename == '':
        return jsonify({
            "valid": False,
            "error": "Empty filename",
            "errors": ["Nombre de archivo vacío"],
            "warnings": [],
            "version": "N/A"
        }), 400
    
    # Verificar extensión
    if not allowed_file(file.filename):
        return jsonify({
            "valid": False,
            "error": "Invalid file type",
            "errors": ["Solo se permiten archivos .epub"],
            "warnings": [],
            "version": "N/A"
        }), 400
    
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Ejecutar EPUBCheck
        result = subprocess.run(
            ['java', '-jar', '/app/epubcheck.jar', tmp_path, '--json', '-'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Limpiar archivo temporal
        os.unlink(tmp_path)
        
        # Parsear resultado JSON de EPUBCheck
        try:
            epub_result = json.loads(result.stdout)
            
            # Extraer información
            messages = epub_result.get('messages', [])
            errors = [m for m in messages if m.get('severity') == 'ERROR']
            warnings = [m for m in messages if m.get('severity') == 'WARNING']
            fatals = [m for m in messages if m.get('severity') == 'FATAL']
            
            is_valid = len(errors) == 0 and len(fatals) == 0
            
            # Obtener versión EPUB
            pub_info = epub_result.get('publication', {})
            epub_version = pub_info.get('epub-version', 'N/A')
            
            return jsonify({
                "valid": is_valid,
                "errors": [e.get('message', '') for e in errors],
                "warnings": [w.get('message', '') for w in warnings],
                "fatals": [f.get('message', '') for f in fatals],
                "version": epub_version,
                "errorCount": len(errors),
                "warningCount": len(warnings),
                "fatalCount": len(fatals),
                "messages": messages[:10]  # Solo primeros 10 mensajes
            })
            
        except json.JSONDecodeError:
            # Si no se puede parsear el JSON, devolver error
            return jsonify({
                "valid": False,
                "error": "EPUBCheck output parsing failed",
                "errors": [result.stderr or "Error al validar el archivo"],
                "warnings": [],
                "version": "N/A"
            }), 500
            
    except subprocess.TimeoutExpired:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({
            "valid": False,
            "error": "Validation timeout",
            "errors": ["La validación tardó demasiado tiempo"],
            "warnings": [],
            "version": "N/A"
        }), 408
        
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({
            "valid": False,
            "error": str(e),
            "errors": [f"Error interno: {str(e)}"],
            "warnings": [],
            "version": "N/A"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)