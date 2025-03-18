#!/usr/bin/env python3
"""
Aplicación de línea de comandos para el Bot de Facebook.
Permite interactuar con publicaciones de Facebook mediante una interfaz simple.

Uso:
    python facebook_cli.py interact --url URL_PUBLICACION [opciones]
    python facebook_cli.py batch --file ARCHIVO_URLS [opciones]

Ejemplos:
    python facebook_cli.py interact --url https://www.facebook.com/example/posts/123456
    python facebook_cli.py batch --file urls.txt --delay 30
"""

import json
import os
import sys
import time
import argparse
import logging
from datetime import datetime

# Importar el bot de Selenium (sin importación condicional ya que ahora solo usamos esta versión)
from facebook_bot_selenium import FacebookBotSelenium, run_facebook_bot

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"facebook_cli_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("FacebookCLI")


def run_bot(post_url, config_file='config.json'):
    """
    Ejecuta el bot para interactuar con una publicación específica de Facebook
    
    Args:
        post_url (str): URL de la publicación de Facebook
        config_file (str): Ruta al archivo de configuración
    """
    # Cargar credenciales desde el archivo de configuración
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
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
            
    except Exception as e:
        logger.error(f"Error al leer el archivo de configuración: {e}")
        return False
    
    # Ejecutar el bot de Selenium directamente
    try:
        logger.info("Usando FacebookBotSelenium para interactuar con Facebook")
        success = run_facebook_bot(
            username=username,
            password=password,
            post_url=post_url,
            like=True,
            comment=True,
            share=False  # Cambiar a True si también quieres compartir
        )
        
        return success
        
    except Exception as e:
        logger.error(f"Error con FacebookBotSelenium: {e}")
        return False


def interact_with_post(args):
    """Interactúa con una única publicación de Facebook"""
    logger.info(f"Interactuando con la publicación: {args.url}")
    
    success = run_bot(
        post_url=args.url,
        config_file=args.config
    )
    
    if success:
        logger.info("EXITOSO: Interacción completada correctamente")
    else:
        logger.error("FALLIDO: La interacción no se completó correctamente")
    
    return success


def batch_process(args):
    """Procesa un lote de publicaciones desde un archivo"""
    if not os.path.exists(args.file):
        logger.error(f"El archivo {args.file} no existe")
        return False
    
    try:
        with open(args.file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Procesando {len(urls)} publicaciones desde {args.file}")
        
        successful = 0
        failed = 0
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Procesando publicación {i}/{len(urls)}: {url}")
            
            success = run_bot(
                post_url=url,
                config_file=args.config
            )
            
            if success:
                successful += 1
                logger.info(f"EXITOSO: Interacción completada correctamente ({successful} exitosas, {failed} fallidas)")
            else:
                failed += 1
                logger.error(f"FALLIDO: La interacción no se completó correctamente ({successful} exitosas, {failed} fallidas)")
            
            # Esperar el tiempo de retraso especificado entre publicaciones
            if i < len(urls):
                logger.info(f"Esperando {args.delay} segundos antes de la siguiente publicación...")
                time.sleep(args.delay)
        
        logger.info(f"Procesamiento por lotes completado. Resultados: {successful} exitosas, {failed} fallidas")
        return failed == 0
        
    except Exception as e:
        logger.error(f"Error durante el procesamiento por lotes: {e}")
        return False


def parse_arguments():
    """Analiza los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description="Bot de interacción con publicaciones de Facebook")
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")
    
    # Comando de interacción con una única publicación
    interact_parser = subparsers.add_parser("interact", help="Interactúa con una única publicación")
    interact_parser.add_argument("--url", required=True, help="URL de la publicación de Facebook")
    interact_parser.add_argument("--config", default="config.json", help="Archivo de configuración (predeterminado: config.json)")
    interact_parser.set_defaults(func=interact_with_post)
    
    # Comando de procesamiento por lotes
    batch_parser = subparsers.add_parser("batch", help="Procesa un lote de publicaciones desde un archivo")
    batch_parser.add_argument("--file", required=True, help="Archivo que contiene las URLs de las publicaciones (una por línea)")
    batch_parser.add_argument("--delay", type=int, default=60, help="Retraso en segundos entre publicaciones (predeterminado: 60)")
    batch_parser.add_argument("--config", default="config.json", help="Archivo de configuración (predeterminado: config.json)")
    batch_parser.set_defaults(func=batch_process)
    
    return parser.parse_args()


def main():
    """Función principal de la aplicación CLI"""
    try:
        # Crear directorio de logs si no existe
        os.makedirs("logs", exist_ok=True)
        
        # Mostrar información sobre el modo del bot
        logger.info("Bot configurado para interactuar realmente con Facebook usando Selenium")
        
        args = parse_arguments()
        
        if args.command is None:
            print("Debe especificar un comando. Use --help para obtener ayuda.")
            sys.exit(1)
        
        result = args.func(args)
        sys.exit(0 if result else 1)
        
    except Exception as e:
        logger.critical(f"Error crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()