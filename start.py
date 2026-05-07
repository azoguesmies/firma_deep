#!/usr/bin/env python3
"""
Iniciar la aplicación completa (backend + servidor frontend)
"""

import subprocess
import sys
import os
import time
import threading
import webbrowser

def start_backend():
    """Iniciar el servidor backend FastAPI"""
    os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))
    subprocess.run([sys.executable, 'api_firma.py'])

def start_frontend():
    """Iniciar servidor para el frontend"""
    os.chdir(os.path.join(os.path.dirname(__file__), 'frontend'))
    subprocess.run([sys.executable, '-m', 'http.server', '8080'])

def open_browser():
    """Abrir el navegador después de unos segundos"""
    time.sleep(2)
    webbrowser.open('http://localhost:8080')

if __name__ == "__main__":
    print("=" * 60)
    print("  FIRMA ELECTRÓNICA ECUADOR - APLICACIÓN COMPLETA")
    print("=" * 60)
    print("  Iniciando backend (API) en puerto 8000...")
    print("  Iniciando frontend en puerto 8080...")
    print("  Abriendo navegador en http://localhost:8080")
    print("=" * 60)
    
    # Iniciar backend en hilo separado
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Esperar a que el backend inicie
    time.sleep(2)
    
    # Iniciar frontend
    frontend_thread = threading.Thread(target=open_browser, daemon=True)
    frontend_thread.start()
    
    start_frontend()