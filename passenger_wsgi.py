import sys
import os

# Asegurar que Python cargue tus scripts locales
sys.path.insert(0, os.path.dirname(__file__))

from a2wsgi import ASGIMiddleware
from main import app

# Inicializamos el puente ASGI a WSGI
wsgi_application = ASGIMiddleware(app)

def application(environ, start_response):
    # 1. Limpiamos SCRIPT_NAME para que no interfiera en el subdominio
    environ['SCRIPT_NAME'] = ''
    
    # 2. Extraemos la ruta real directamente desde lo que el navegador solicita (REQUEST_URI)
    # Esto elimina parámetros de consulta tipo '?query=param' para que FastAPI entienda la ruta pura
    request_uri = environ.get('REQUEST_URI', '/')
    path_info = request_uri.split('?')[0]
    
    # 3. Forzamos a Passenger a usar esta ruta limpia
    environ['PATH_INFO'] = path_info
        
    return wsgi_application(environ, start_response)

