import time
import random
import json
import logging
import os
from datetime import datetime
import configparser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("facebook_selenium_bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("FacebookSeleniumBot")

# Clase base para todos los bots de redes sociales
class SocialMediaBot:
    def __init__(self, username, password, config_file='config.ini'):
        self.username = username
        self.password = password
        self.session = None
        self.connected = False
        self.config = self._load_config(config_file)
        self.comment_templates = self._load_comments('comments.json')
        
    def _load_config(self, config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        return config
        
    def _load_comments(self, comments_file):
        try:
            with open(comments_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo de comentarios {comments_file} no encontrado. Usando comentarios predeterminados.")
            return {
                "general": [
                    "¡Excelente publicación!",
                    "Muy interesante contenido",
                    "Me encanta esto 👍",
                    "Gracias por compartir",
                    "Impresionante 🔥"
                ]
            }
    
    def login(self):
        """Método para iniciar sesión en la plataforma"""
        raise NotImplementedError("Cada plataforma debe implementar su propio método de login")
    
    def like_post(self, post_url):
        """Método para dar like a una publicación"""
        raise NotImplementedError("Cada plataforma debe implementar su propio método de like")
    
    def comment_post(self, post_url, comment=None):
        """Método para comentar en una publicación"""
        if not comment:
            comment = random.choice(self.comment_templates["general"])
        
        raise NotImplementedError("Cada plataforma debe implementar su propio método de comentario")
    
    def interact_with_feed(self, num_interactions=10, comment_probability=0.3):
        """Método para interactuar con el feed"""
        raise NotImplementedError("Cada plataforma debe implementar su propio método de interacción")
    
    def save_activity_log(self, action, post_url, status, details=None):
        """Guardar registro de actividad para reportes"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "platform": self.__class__.__name__,
            "username": self.username,
            "action": action,
            "post_url": post_url,
            "status": status,
            "details": details
        }
        
        try:
            with open(f"logs/{self.username}_activity.json", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Error guardando log de actividad: {e}")

class FacebookBotSelenium(SocialMediaBot):
    def __init__(self, username, password, config_file='config.ini'):
        super().__init__(username, password, config_file)
        self.platform = "Facebook"
        self.driver = None
        self.wait = None
        
        # Cargar configuración del navegador desde config.json si existe
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config_json = json.load(f)
                self.browser_settings = config_json.get('browser_settings', {})
        except:
            self.browser_settings = {
                'headless': False,
                'wait_time': 10
            }
    
    def _setup_browser(self):
        """Configurar el navegador para la automatización"""
        headless = self.browser_settings.get('headless', False)
        wait_time = self.browser_settings.get('wait_time', 10)
        
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Configuraciones para mejorar la automatización
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, wait_time)
            return True
        except Exception as e:
            logger.error(f"Error al configurar el navegador: {e}")
            return False
    
    def login(self):
        """Inicia sesión en Facebook usando Selenium"""
        try:
            if not self.driver:
                if not self._setup_browser():
                    return False
            
            logger.info(f"Iniciando sesión en Facebook como {self.username}")
            
            # Navegar a la página de inicio de sesión
            self.driver.get("https://www.facebook.com/")
            
            # Aceptar cookies si aparece el diálogo
            try:
                cookie_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Aceptar') or contains(text(), 'Accept') or contains(text(), 'Permitir')]"))
                )
                cookie_button.click()
                time.sleep(1)
            except:
                logger.info("No se encontró diálogo de cookies o ya fue aceptado")
            
            try:
                # Ingresar email
                email_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
                email_field.clear()
                email_field.send_keys(self.username)
                
                # Ingresar contraseña
                password_field = self.wait.until(
                    EC.presence_of_element_located((By.ID, "pass"))
                )
                password_field.clear()
                password_field.send_keys(self.password)
                
                # Hacer clic en el botón de inicio de sesión
                login_button = self.wait.until(
                    EC.element_to_be_clickable((By.NAME, "login"))
                )
                login_button.click()
                
                # Esperar a que la página principal se cargue (esperar más tiempo)
                time.sleep(5)
                
                # Verificar si hay mensajes de error de inicio de sesión
                try:
                    error_message = self.driver.find_element(By.XPATH, "//div[contains(@class, 'login_error_box')]")
                    logger.error(f"Error de inicio de sesión: {error_message.text}")
                    return False
                except NoSuchElementException:
                    # No se encontró mensaje de error, continuar
                    pass
                
                # Verificar si hay solicitud de código de seguridad
                try:
                    security_code_field = self.driver.find_element(By.ID, "approvals_code")
                    logger.error("Se requiere autenticación de dos factores. No se puede iniciar sesión automáticamente.")
                    return False
                except NoSuchElementException:
                    # No se requiere código de seguridad, continuar
                    pass
                
                # Verificar si el inicio de sesión fue exitoso
                current_url = self.driver.current_url
                if "facebook.com/home" in current_url or "facebook.com/?sk=h_chr" in current_url or "facebook.com/" in current_url:
                    logger.info("Inicio de sesión exitoso")
                    self.connected = True
                    return True
                else:
                    logger.error(f"No se pudo verificar el inicio de sesión exitoso. URL actual: {current_url}")
                    return False
            
            except Exception as e:
                logger.error(f"Error durante la entrada de credenciales: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error durante el inicio de sesión: {e}")
            return False
    
    def like_post(self, post_url):
        """Da like a una publicación de Facebook"""
        if not self.connected:
            if not self.login():
                return False
        
        try:
            logger.info(f"Dando like a la publicación: {post_url}")
            
            # Navegar a la URL de la publicación
            self.driver.get(post_url)
            time.sleep(3)
            
            # Encontrar y hacer clic en el botón de like
            try:
                # Intentar encontrar el botón de like por texto
                like_paths = [
                    "//span[text()='Me gusta']/ancestor::div[@role='button']",
                    "//span[text()='Like']/ancestor::div[@role='button']",
                    "//div[@aria-label='Me gusta' or @aria-label='Like']",
                    "//div[@data-testid='UFI2ReactionLink']"
                ]
                
                for xpath in like_paths:
                    try:
                        like_button = self.wait.until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", like_button)
                        time.sleep(1)
                        like_button.click()
                        logger.info("Botón de like encontrado y clicado")
                        break
                    except:
                        continue
                else:
                    # Si salimos del bucle sin encontrar el botón
                    logger.warning("No se pudo encontrar el botón de like con los selectores conocidos")
                    # Intentamos capturar todos los botones visibles para debugging
                    buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']")
                    logger.info(f"Botones encontrados: {len(buttons)}")
                    
                    # Intento último recurso - primer botón que parezca like
                    for btn in buttons:
                        try:
                            aria_label = btn.get_attribute("aria-label")
                            if aria_label and ("like" in aria_label.lower() or "me gusta" in aria_label.lower()):
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.info(f"Intentado clic en botón con aria-label: {aria_label}")
                                break
                        except:
                            continue
            
                # Esperar un momento para que se registre el like
                time.sleep(2)
                
                # Registrar actividad
                self.save_activity_log("like", post_url, "success")
                return True
            
            except Exception as e:
                logger.error(f"Error al interactuar con el botón de like: {e}")
                self.save_activity_log("like", post_url, "error", str(e))
                return False
            
        except Exception as e:
            logger.error(f"Error al dar like a la publicación: {e}")
            self.save_activity_log("like", post_url, "error", str(e))
            return False
    
    def comment_post(self, post_url, comment=None):
        """Comenta en una publicación de Facebook"""
        if not self.connected:
            if not self.login():
                return False
        
        if not comment:
            comment = random.choice(self.comment_templates["general"])
        
        try:
            logger.info(f"Comentando en la publicación: {post_url}")
            logger.info(f"Comentario: {comment}")
            
            # Si no estamos ya en la URL de la publicación, navegar a ella
            current_url = self.driver.current_url
            if post_url not in current_url:
                self.driver.get(post_url)
                time.sleep(3)
            
            # Buscar el área de comentario
            comment_selectors = [
                "//div[@contenteditable='true' and @role='textbox' and contains(@aria-label, 'coment') or contains(@aria-label, 'Comment')]",
                "//div[@contenteditable='true' and @role='textbox']",
                "//div[@role='textbox' and @aria-label='Escribe un comentario' or @aria-label='Write a comment']",
                "//form//div[@contenteditable='true']",
                "//form//div[@role='textbox']"
            ]
            
            # Intentar cada selector hasta encontrar uno que funcione
            for selector in comment_selectors:
                try:
                    comment_area = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    
                    # Hacer scroll hasta el área de comentario y hacer clic
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", comment_area)
                    time.sleep(1)
                    comment_area.click()
                    time.sleep(1)
                    
                    # Escribir el comentario
                    comment_area.send_keys(comment)
                    time.sleep(2)
                    
                    # Enviar el comentario con Enter
                    comment_area.send_keys("\n")
                    time.sleep(3)
                    
                    # Registrar actividad
                    self.save_activity_log("comment", post_url, "success", {"comment": comment})
                    return True
                except:
                    continue
            
            # Si ningún selector funcionó
            logger.error("No se pudo encontrar el área de comentario")
            return False
            
        except Exception as e:
            logger.error(f"Error comentando en la publicación: {e}")
            self.save_activity_log("comment", post_url, "error", str(e))
            return False
    
    def share_post(self, post_url):
        """Comparte una publicación de Facebook"""
        if not self.connected:
            if not self.login():
                return False
                
        try:
            logger.info(f"Compartiendo la publicación: {post_url}")
            
            # Navegar a la URL de la publicación si no estamos ya allí
            current_url = self.driver.current_url
            if post_url not in current_url:
                self.driver.get(post_url)
                time.sleep(3)
            
            # Encontrar y hacer clic en el botón de compartir
            share_button = None
            share_selectors = [
                "//span[text()='Compartir' or text()='Share']/ancestor::div[@role='button']",
                "//div[@aria-label='Compartir' or @aria-label='Share']",
                "//div[contains(@aria-label, 'ompart') or contains(@aria-label, 'hare')]"
            ]
            
            for selector in share_selectors:
                try:
                    share_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", share_button)
                    time.sleep(1)
                    share_button.click()
                    time.sleep(2)
                    break
                except:
                    continue
            
            if not share_button:
                logger.error("No se pudo encontrar el botón de compartir")
                return False
            
            # Buscar la opción "Compartir ahora"/"Share now"
            share_now_selectors = [
                "//span[text()='Compartir ahora' or text()='Share now']/ancestor::div[@role='button']",
                "//div[@role='button' and @aria-label='Compartir ahora' or @aria-label='Share now']",
                "//div[contains(text(), 'ompartir ahora') or contains(text(), 'hare now')]"
            ]
            
            for selector in share_now_selectors:
                try:
                    share_now = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    share_now.click()
                    time.sleep(3)
                    
                    # Registrar actividad
                    self.save_activity_log("share", post_url, "success")
                    return True
                except:
                    continue
            
            logger.error("No se pudo encontrar la opción 'Compartir ahora'")
            return False
            
        except Exception as e:
            logger.error(f"Error al compartir la publicación: {e}")
            self.save_activity_log("share", post_url, "error", str(e))
            return False
    
    def interact_with_post(self, post_url, like=True, comment=True, share=False):
        """Interactúa con una publicación específica (like, comentario, compartir)"""
        if not self.connected:
            if not self.login():
                return False
        
        success = True
        
        # Navegar a la URL de la publicación
        self.driver.get(post_url)
        time.sleep(3)
        
        # Dar like si se solicita
        if like:
            like_success = self.like_post(post_url)
            if not like_success:
                success = False
        
        # Comentar si se solicita
        if comment:
            comment_success = self.comment_post(post_url)
            if not comment_success:
                success = False
        
        # Compartir si se solicita
        if share:
            share_success = self.share_post(post_url)
            if not share_success:
                success = False
        
        return success
    
    def close(self):
        """Cierra el navegador y limpia los recursos"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Navegador cerrado correctamente")
            except Exception as e:
                logger.error(f"Error al cerrar el navegador: {e}")

# Función para usar el bot directamente
def run_facebook_bot(username, password, post_url, like=True, comment=True, share=False):
    """
    Función para ejecutar el bot de Facebook directamente
    
    Args:
        username (str): Correo electrónico o nombre de usuario de Facebook
        password (str): Contraseña de Facebook
        post_url (str): URL de la publicación con la que interactuar
        like (bool): Si se debe dar like a la publicación
        comment (bool): Si se debe comentar en la publicación
        share (bool): Si se debe compartir la publicación
    
    Returns:
        bool: True si todas las interacciones solicitadas fueron exitosas
    """
    # Asegurar que exista el directorio de logs
    os.makedirs("logs", exist_ok=True)
    
    bot = FacebookBotSelenium(username, password)
    
    try:
        # Iniciar sesión
        login_success = bot.login()
        if not login_success:
            logger.error("No se pudo iniciar sesión. Abortando.")
            bot.close()
            return False
        
        # Interactuar con la publicación
        interaction_success = bot.interact_with_post(
            post_url=post_url,
            like=like,
            comment=comment,
            share=share
        )
        
        # Cerrar el bot
        bot.close()
        return interaction_success
        
    except Exception as e:
        logger.error(f"Error durante la ejecución del bot: {e}")
        bot.close()
        return False

# Si se ejecuta directamente
if __name__ == "__main__":
    import sys
    
    # Asegurar que exista el directorio de logs
    os.makedirs("logs", exist_ok=True)
    
    if len(sys.argv) > 2:
        # Usar credenciales proporcionadas como argumentos
        username = sys.argv[1]
        password = sys.argv[2]
        
        if len(sys.argv) > 3:
            # Interactuar con URL proporcionada
            url = sys.argv[3]
            run_facebook_bot(username, password, url)
        else:
            print("No se proporcionó URL para interactuar")
    else:
        print("Uso: python facebook_bot_selenium.py <username> <password> [url]")