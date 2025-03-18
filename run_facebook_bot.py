#!/usr/bin/env python3
"""
Script para ejecutar el bot de Facebook con Selenium.
Este script simplifica el uso del bot de Facebook para interactuar con publicaciones.

Uso:
    python run_facebook_bot.py <url_publicacion>
    
Ejemplos:
    python run_facebook_bot.py https://www.facebook.com/share/p/123456789
"""

import os
import sys
import json
import logging
from facebook_bot_selenium import FacebookBotSelenium, run_facebook_bot

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("run_facebook_bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("FacebookBotLauncher")

def main():
    """Función principal del script"""
    # Crear directorio de logs si no existe
    os.makedirs("logs", exist_ok=True)
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        post_url = sys.argv[1]
    else:
        print("Error: No se proporcionó URL de la publicación")
        print("Uso: python run_facebook_bot.py <url_publicacion>")
        return False
    
    # Cargar credenciales desde config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if not config.get('accounts') or len(config['accounts']) == 0:
            logger.error("No se encontraron cuentas en el archivo de configuración")
            return False
        
        account = config['accounts'][0]
        username = account.get('username')
        password = account.get('password')
        
        if not username or not password:
            logger.error("Falta username o password en la configuración")
            return False
            
        logger.info(f"Configuración cargada para usuario: {username}")
            
    except Exception as e:
        logger.error(f"Error al leer el archivo de configuración: {e}")
        return False
    
    # Mostrar información de lo que se va a hacer
    logger.info(f"Iniciando interacción con publicación: {post_url}")
    logger.info(f"Usuario: {username}")
    logger.info("Acciones: Dar Like y Comentar")
    
    # Ejecutar el bot
    success = run_facebook_bot(
        username=username,
        password=password,
        post_url=post_url,
        like=True,
        comment=True,
        share=False  # Cambiar a True si también quieres compartir
    )
    
    if success:
        logger.info("EXITOSO: Interacción completada correctamente")
    else:
        logger.error("FALLIDO: La interacción no se completó correctamente")
    
    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario")
    except Exception as e:
        logger.critical(f"Error crítico: {e}")
        sys.exit(1)