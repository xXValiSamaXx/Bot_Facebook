import time
import random
import json
import logging
import os
import sys
import io
from datetime import datetime
import configparser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# Configurar stdout para manejar Unicode correctamente
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("facebook_selenium_bot.log", encoding='utf-8'),
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
                    "Me encanta esto",
                    "Gracias por compartir",
                    "Impresionante"
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
            # Filtrar comentarios que contengan emojis para evitar errores de codificación
            text_comments = [c for c in self.comment_templates["general"] 
                          if not any(ord(char) > 127 for char in c)]
            
            if text_comments:
                comment = random.choice(text_comments)
            else:
                comment = "Muy interesante!"
        
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
            with open(f"logs/{self.username}_activity.json", "a", encoding='utf-8') as f:
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
            
            # Convertir la URL a versión de escritorio si es móvil
            login_url = "https://www.facebook.com/"
            
            # Navegar a la página de inicio de sesión
            self.driver.get(login_url)
            
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
        
            # Abrir en nueva pestaña
            self.driver.execute_script(f"window.open('{post_url}', '_blank');")
        
            # Cambiar al nuevo tab
            self.driver.switch_to.window(self.driver.window_handles[-1])

            time.sleep(5)
        
            # El resto del código continúa igual...
            
            # Detectar si estamos en la versión móvil
            is_mobile = "m.facebook.com" in self.driver.current_url
            
            if is_mobile:
                # Selectores específicos para versión móvil
                like_paths = [
                    "//a[contains(@aria-label, 'Me gusta') or contains(@aria-label, 'Like')]",
                    "//a[starts-with(@data-sigil, 'ufi-inline-like')]",
                    "//a[contains(@href, 'reaction_type=1')]",
                    "//a[contains(@class, 'like-reaction')]",
                    "//span[text()='Me gusta']/parent::a",
                    "//div[@role='button']/span[text()='Me gusta' or text()='Like']/.."
                ]
            else:
                # Selectores para versión de escritorio
                like_paths = [
                    "//div[@aria-label='Me gusta' or @aria-label='Like']",
                    "//div[contains(@aria-label, 'Me gusta') or contains(@aria-label, 'Like')]",
                    "//span[text()='Me gusta']/parent::div",
                    "//span[contains(text(), 'Me gusta')]/ancestor::div[@role='button']",
                    "//div[contains(@aria-label, 'personas') and contains(@aria-label, 'Me gusta')]",
                    "//div[@role='button' and contains(@aria-label, 'Me gusta')]",
                    "//div[@role='button' and contains(@aria-label, 'Like')]"
                ]
            
            like_button_found = False
            for xpath in like_paths:
                try:
                    # Agregar un scroll para asegurar que el botón está visible
                    self.driver.execute_script("window.scrollBy(0, 300);")
                    time.sleep(1)
                    
                    # Buscar el botón
                    like_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    
                    # Ejecutar JavaScript click para evitar problemas de interacción
                    self.driver.execute_script("arguments[0].click();", like_button)
                    logger.info(f"Botón de like encontrado y clicado con selector: {xpath}")
                    like_button_found = True
                    
                    # Esperar un momento para confirmar que el like se registró
                    time.sleep(3)
                    
                    # Registrar actividad
                    self.save_activity_log("like", post_url, "success")
                    return True
                except Exception as e:
                    continue
            
            # Si no se encontró con los selectores específicos, intentar con el método alternativo
            if not like_button_found:
                logger.warning("Intentando método alternativo para encontrar el botón de like")
                try:
                    # Buscar los botones de reacción por sus atributos parciales
                    if is_mobile:
                        buttons = self.driver.find_elements(By.XPATH, "//a[@role='button' or contains(@data-sigil, 'touchable')]")
                    else:
                        buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']")
                    
                    logger.info(f"Botones encontrados: {len(buttons)}")
                    
                    for btn in buttons:
                        try:
                            aria_label = btn.get_attribute("aria-label")
                            if aria_label and ("me gusta" in aria_label.lower() or "like" in aria_label.lower()):
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.info(f"Clic en botón con aria-label: {aria_label}")
                                
                                # Registrar actividad
                                self.save_activity_log("like", post_url, "success")
                                return True
                        except:
                            continue
                except Exception as e:
                    logger.error(f"Error en método alternativo de like: {e}")
            
            logger.error("No se pudo encontrar ningún botón de like")
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
            # Filtrar comentarios que contengan emojis para evitar errores de codificación
            text_comments = [c for c in self.comment_templates["general"] 
                          if not any(ord(char) > 127 for char in c)]
            
            if text_comments:
                comment = random.choice(text_comments)
            else:
                comment = "Muy interesante!"
        
        try:
            logger.info(f"Comentando en la publicación: {post_url}")
            # Registrar el comentario de forma segura evitando problemas de codificación
            try:
                safe_comment = comment.encode('ascii', 'replace').decode('ascii')
                logger.info(f"Comentario: {safe_comment}")
            except:
                logger.info("Comentario con caracteres especiales seleccionado")
            
            # No convertir automáticamente la URL
            # Usar la URL exacta proporcionada
            
            # Si no estamos ya en una página de Facebook, navegar a ella
            current_url = self.driver.current_url
            if "facebook.com" not in current_url:
                self.driver.get(post_url)
                time.sleep(5)
            
            # Detectar si estamos en la versión móvil
            is_mobile = "m.facebook.com" in self.driver.current_url
            
            # Hacer scroll hacia abajo para asegurar que se cargan los comentarios
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            
            if is_mobile:
                logger.info("Detectada versión móvil de Facebook, usando selectores móviles")
                
                # Primero, buscar y hacer clic en el botón de comentario en móvil
                mobile_comment_buttons = [
                    "//a[contains(text(), 'Comentar') or contains(text(), 'Comment')]",
                    "//span[contains(text(), 'Comentar') or contains(text(), 'Comment')]",
                    "//a[starts-with(@data-sigil, 'feed-ufi-focus')]",
                    "//a[contains(@data-uri, 'comment')]",
                    "//a[contains(@aria-label, 'comentar') or contains(@aria-label, 'comment')]"
                ]
                
                for selector in mobile_comment_buttons:
                    try:
                        comment_btn = self.driver.find_element(By.XPATH, selector)
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_btn)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", comment_btn)
                        logger.info(f"Botón comentar móvil encontrado y clicado: {selector}")
                        time.sleep(3)  # Esperar más tiempo para que cargue el área de comentario
                        break
                    except:
                        continue
                
                # Buscar el área de texto para comentarios en móvil
                mobile_textareas = [
                    "//textarea[@id='composerInput']",
                    "//textarea[contains(@placeholder, 'coment') or contains(@placeholder, 'Comment')]",
                    "//textarea[@name='comment_text']",
                    "//textarea[contains(@id, 'comment')]",
                    "//textarea"
                ]
                
                for selector in mobile_textareas:
                    try:
                        textarea = self.wait.until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        
                        # Intentar interactuar con el textarea
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
                        time.sleep(1)
                        textarea.click()
                        time.sleep(1)
                        
                        # Limpiar y enviar texto
                        try:
                            textarea.clear()
                            time.sleep(0.5)
                        except:
                            pass
                        
                        textarea.send_keys(comment)
                        time.sleep(2)
                        
                        # Buscar y hacer clic en el botón de publicar
                        post_buttons = [
                            "//input[@type='submit']",
                            "//button[@type='submit']",
                            "//button[contains(text(), 'Publicar') or contains(text(), 'Post')]",
                            "//button[@value='Post']",
                            "//button[contains(@data-sigil, 'submit')]"
                        ]
                        
                        button_clicked = False
                        for btn_selector in post_buttons:
                            try:
                                submit_btn = self.driver.find_element(By.XPATH, btn_selector)
                                self.driver.execute_script("arguments[0].click();", submit_btn)
                                logger.info(f"Botón publicar encontrado y clicado: {btn_selector}")
                                button_clicked = True
                                time.sleep(3)
                                break
                            except:
                                continue
                        
                        if not button_clicked:
                            # Si no se encontró botón, intentar con Enter
                            textarea.send_keys(Keys.ENTER)
                            logger.info("Enviado comentario con tecla Enter")
                            time.sleep(3)
                        
                        # Registrar actividad
                        self.save_activity_log("comment", post_url, "success", {"comment": comment})
                        return True
                    except Exception as e:
                        logger.debug(f"Error con textarea móvil {selector}: {str(e)}")
                        continue
                
                # Si no funcionaron los selectores móviles específicos, tomar captura para depuración
                try:
                    screenshot_path = f"logs/screenshot_mobile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Captura de pantalla guardada en {screenshot_path}")
                except:
                    pass
                
            else:
                # Versión de escritorio
                # Primero, buscar y hacer clic en el botón "Comentar" si existe
                comment_button_selectors = [
                    "//span[text()='Comentar' or text()='Comment']/ancestor::div[@role='button']",
                    "//div[@aria-label='Comentar' or @aria-label='Comment']",
                    "//a[@aria-label='Comentar' or @aria-label='Comment']"
                ]
                
                for selector in comment_button_selectors:
                    try:
                        comment_button = self.driver.find_element(By.XPATH, selector)
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", comment_button)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", comment_button)
                        logger.info("Botón de comentar encontrado y clicado")
                        time.sleep(2)
                        break
                    except:
                        continue
                
                # Actualizar selectores para encontrar el área de comentarios
                comment_selectors = [
                    # Más específicos primero
                    "//div[@aria-label='Escribe un comentario...' or @aria-label='Write a comment...']",
                    "//div[@contenteditable='true' and @role='textbox']",
                    "//form[@role='presentation']//div[@contenteditable='true']",
                    # Buscar por placeholder también
                    "//div[@data-placeholder='Escribe un comentario...' or @data-placeholder='Write a comment...']",
                    # Buscar la sección de comentarios primero y luego el área de texto
                    "//div[contains(@aria-label, 'comentario') or contains(@aria-label, 'comment')]",
                    # Métodos alternativos basados en la estructura general
                    "//span[text()='Comentar' or text()='Comment']/ancestor::div[@role='button']"
                ]
                
                # Ahora buscar el área de comentario
                for selector in comment_selectors:
                    try:
                        comment_area = self.wait.until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        
                        # Scroll y clic
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_area)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", comment_area)
                        time.sleep(1)
                        
                        # Intentar limpiar el área primero
                        try:
                            comment_area.clear()
                        except:
                            pass
                        
                        # Usar JavaScript para establecer el valor
                        self.driver.execute_script("arguments[0].textContent = arguments[1];", comment_area, comment)
                        time.sleep(1)
                        
                        # Método alternativo: enviar teclas
                        comment_area.send_keys(comment)
                        time.sleep(2)
                        
                        # Enviar con Enter
                        comment_area.send_keys(Keys.ENTER)
                        time.sleep(3)
                        
                        # Registrar actividad
                        self.save_activity_log("comment", post_url, "success", {"comment": comment})
                        logger.info(f"Comentario enviado exitosamente: {comment}")
                        return True
                    except Exception as e:
                        logger.debug(f"Error con selector {selector}: {e}")
                        continue
            
            # Si ninguno de los métodos anteriores funcionó, intentar un enfoque más genérico
            try:
                logger.warning("Intentando método alternativo para encontrar el área de comentario")
                
                # Buscar elementos que puedan ser el área de comentario
                if is_mobile:
                    # En móvil, buscar textareas o inputs
                    potential_elements = self.driver.find_elements(By.XPATH, "//textarea | //input[@type='text']")
                else:
                    # En escritorio, buscar áreas editables o campos de formulario
                    potential_elements = self.driver.find_elements(By.XPATH, "//div[@contenteditable='true'] | //div[@role='textbox']")
                
                logger.info(f"Elementos potenciales encontrados: {len(potential_elements)}")
                
                for element in potential_elements:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(1)
                        
                        # Probar si podemos escribir en este elemento
                        element.send_keys(comment)
                        time.sleep(1)
                        element.send_keys(Keys.ENTER)
                        time.sleep(3)
                        
                        logger.info("Comentario posiblemente enviado con elemento alternativo")
                        self.save_activity_log("comment", post_url, "success", {"comment": comment})
                        return True
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error en método alternativo final: {e}")
            
            # Tomar captura de pantalla para depuración
            try:
                screenshot_path = f"logs/error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Captura de error guardada en {screenshot_path}")
            except:
                pass
            
            # Si llegamos aquí, no se pudo encontrar el área de comentario
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
            
            # No convertir la URL automáticamente
            
            # Navegar a la URL de la publicación si no estamos ya allí
            current_url = self.driver.current_url
            if "facebook.com" not in current_url:
                self.driver.get(post_url)
                time.sleep(5)
            
            # Detectar si estamos en la versión móvil
            is_mobile = "m.facebook.com" in self.driver.current_url
            
            if is_mobile:
                # Selectores para versión móvil
                share_selectors = [
                    "//a[contains(text(), 'Compartir') or contains(text(), 'Share')]",
                    "//span[contains(text(), 'Compartir') or contains(text(), 'Share')]/parent::a",
                    "//a[contains(@href, 'share')]",
                    "//a[contains(@data-sigil, 'share')]"
                ]
                
                share_now_selectors = [
                    "//a[contains(text(), 'Compartir ahora') or contains(text(), 'Share now')]",
                    "//span[contains(text(), 'Compartir ahora') or contains(text(), 'Share now')]/parent::a",
                    "//a[contains(@href, 'share_now')]"
                ]
            else:
                # Selectores para versión de escritorio
                share_selectors = [
                    "//span[text()='Compartir' or text()='Share']/ancestor::div[@role='button']",
                    "//div[@aria-label='Compartir' or @aria-label='Share']",
                    "//div[contains(@aria-label, 'ompart') or contains(@aria-label, 'hare')]"
                ]
                
                share_now_selectors = [
                    "//span[text()='Compartir ahora' or text()='Share now']/ancestor::div[@role='button']",
                    "//div[@role='button' and @aria-label='Compartir ahora' or @aria-label='Share now']",
                    "//div[contains(text(), 'ompartir ahora') or contains(text(), 'hare now')]"
                ]
            
            # Encontrar y hacer clic en el botón de compartir
            share_button = None
            for selector in share_selectors:
                try:
                    share_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", share_button)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", share_button)
                    logger.info(f"Botón compartir encontrado y clicado: {selector}")
                    time.sleep(2)
                    break
                except:
                    continue
            
            if not share_button:
                logger.error("No se pudo encontrar el botón de compartir")
                return False
            
            # Buscar la opción "Compartir ahora"/"Share now"
            share_now_found = False
            for selector in share_now_selectors:
                try:
                    share_now = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.driver.execute_script("arguments[0].click();", share_now)
                    logger.info(f"Opción 'Compartir ahora' encontrada y clicada: {selector}")
                    share_now_found = True
                    time.sleep(3)
                    break
                except:
                    continue
            
            if not share_now_found:
                logger.error("No se pudo encontrar la opción 'Compartir ahora'")
                return False
            
            # Registrar actividad
            self.save_activity_log("share", post_url, "success")
            return True
            
        except Exception as e:
            logger.error(f"Error al compartir la publicación: {e}")
            self.save_activity_log("share", post_url, "error", str(e))
            return False
    
    # Método auxiliar para verificar si un elemento está visible
    def is_element_visible(self, element):
        """Verifica si un elemento está visible en la pantalla"""
        try:
            return element.is_displayed() and element.is_enabled()
        except:
            return False
    
    def find_specific_post(self, post_url):
        """
        Encuentra una publicación específica en la página y se posiciona sobre ella.
        Útil cuando Facebook carga múltiples publicaciones en la misma página.
        
        Args:
            post_url (str): La URL de la publicación a encontrar
        
        Returns:
            bool: True si encontró la publicación, False en caso contrario
        """
        logger.info("Intentando identificar la publicación específica...")
        
        # Extraer el ID de la publicación de la URL
        post_id = None
        url_parts = post_url.split('/')
        for part in url_parts:
            if part.startswith('pfbid'):
                post_id = part
                logger.info(f"Buscando publicación con ID: {post_id}")
                break
        
        # Si no podemos identificar el ID, intentaremos buscar por otros métodos
        if not post_id:
            logger.warning("No se pudo identificar el ID de la publicación en la URL")
        
        # 1. Esperamos a que la página cargue completamente
        time.sleep(5)
        
        # Tomar captura para verificar qué estamos viendo
        try:
            screenshot_path = f"logs/initial_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Captura inicial guardada en {screenshot_path}")
        except:
            pass
        
        # 2. Primero intentamos buscar por el ID de la publicación directamente
        if post_id:
            try:
                # Buscar elementos que contengan el ID de la publicación
                post_elements = self.driver.find_elements(By.XPATH, f"//*[contains(@id, '{post_id}')]")
                
                if post_elements:
                    logger.info(f"Encontrados {len(post_elements)} elementos con el ID de la publicación")
                    # Nos desplazamos al primer elemento encontrado
                    element = post_elements[0]
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
                    time.sleep(2)
                    return True
            except Exception as e:
                logger.debug(f"Error buscando por ID: {e}")
        
        # 3. Si no encontramos por ID, intentamos localizar por la estructura de la publicación
        try:
            # Buscar todas las publicaciones (posts) en la página
            is_mobile = "m.facebook.com" in self.driver.current_url
            
            if is_mobile:
                post_selectors = [
                    "//div[contains(@data-ft, 'top_level_post_id')]",
                    "//article[contains(@data-store, 'actor')]",
                    "//div[contains(@data-sigil, 'story')]",
                    "//div[contains(@class, 'story_body_container')]"
                ]
            else:
                post_selectors = [
                    "//div[@role='article']",
                    "//div[contains(@class, 'userContentWrapper')]",
                    "//div[contains(@data-testid, 'post_container')]",
                    "//div[contains(@aria-posinset, '1')]"  # Normalmente el primer post tiene posinset="1"
                ]
            
            posts_found = []
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        posts_found.extend(elements)
                        logger.info(f"Encontrados {len(elements)} posts con el selector: {selector}")
                except:
                    continue
            
            logger.info(f"Total de publicaciones encontradas: {len(posts_found)}")
            
            # Si encontramos publicaciones, nos desplazamos a la primera (que debería ser la nuestra)
            if posts_found:
                # Tomamos el primero que es generalmente la publicación que buscamos
                target_post = posts_found[0]
                
                # Desplazarse a la publicación
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                    target_post
                )
                time.sleep(2)
                
                # Intentar resaltar visualmente la publicación para la depuración
                try:
                    self.driver.execute_script(
                        "arguments[0].style.border='3px solid red'; arguments[0].style.padding='10px';", 
                        target_post
                    )
                except:
                    pass
                
                # Tomar captura para verificar
                try:
                    screenshot_path = f"logs/target_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Captura de publicación objetivo guardada en {screenshot_path}")
                except:
                    pass
                
                # Buscar los botones dentro de esta publicación específica
                target_post_id = target_post.get_attribute("id")
                if target_post_id:
                    logger.info(f"ID del elemento de la publicación identificada: {target_post_id}")
                
                return True
            
            logger.warning("No se encontraron publicaciones en la página")
            return False
            
        except Exception as e:
            logger.error(f"Error buscando publicaciones: {e}")
            return False
    
    def like_post_in_current_view(self, post_url):
        """Da like a la publicación que está actualmente en vista (después de find_specific_post)"""
        if not self.connected:
            if not self.login():
                return False
        
        try:
            logger.info(f"Dando like a la publicación actualmente en vista")
            
            # Detectar si estamos en la versión móvil
            is_mobile = "m.facebook.com" in self.driver.current_url
            
            # Primero buscar los botones solo dentro del área visible o de la publicación identificada
            visible_area = self.driver.find_element(By.XPATH, "//body")
            
            # Desplazarse un poco hacia abajo para ver la sección de likes
            # La mayoría de publicaciones tienen los botones de interacción en la parte inferior
            self.driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(2)
            
            # Tomar captura para depuración
            try:
                screenshot_path = f"logs/before_like_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Captura antes de dar like guardada en {screenshot_path}")
            except:
                pass
            
            if is_mobile:
                # Selectores específicos para versión móvil
                like_paths = [
                    "//a[contains(@aria-label, 'Me gusta') or contains(@aria-label, 'Like')]",
                    "//a[starts-with(@data-sigil, 'ufi-inline-like')]",
                    "//a[contains(@href, 'reaction_type=1')]",
                    "//a[contains(@class, 'like-reaction')]",
                    "//span[text()='Me gusta']/parent::a",
                    "//div[@role='button']/span[text()='Me gusta' or text()='Like']/.."
                ]
            else:
                # Selectores para versión de escritorio
                like_paths = [
                    "//div[@aria-label='Me gusta' or @aria-label='Like']",
                    "//div[contains(@aria-label, 'Me gusta') or contains(@aria-label, 'Like')]",
                    "//span[text()='Me gusta']/parent::div",
                    "//span[contains(text(), 'Me gusta')]/ancestor::div[@role='button']",
                    "//div[contains(@aria-label, 'personas') and contains(@aria-label, 'Me gusta')]",
                    "//div[@role='button' and contains(@aria-label, 'Me gusta')]",
                    "//div[@role='button' and contains(@aria-label, 'Like')]"
                ]
            
            like_button_found = False
            for xpath in like_paths:
                try:
                    # Buscar el botón
                    like_buttons = self.driver.find_elements(By.XPATH, xpath)
                    
                    if like_buttons:
                        # Tomar el primer botón de like visible
                        for button in like_buttons:
                            if self.is_element_visible(button):
                                # Desplazarse al botón
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                                time.sleep(1)
                                
                                # Ejecutar JavaScript click
                                self.driver.execute_script("arguments[0].click();", button)
                                logger.info(f"Botón de like encontrado y clicado con selector: {xpath}")
                                like_button_found = True
                                
                                # Esperar un momento para confirmar que el like se registró
                                time.sleep(3)
                                
                                # Registrar actividad
                                self.save_activity_log("like", post_url, "success")
                                return True
                except Exception as e:
                    continue
            
            # Si no se encontró con los selectores específicos, intentar método alternativo
            if not like_button_found:
                logger.warning("Intentando método alternativo para encontrar el botón de like")
                try:
                    # Buscar los botones de reacción por sus atributos parciales
                    if is_mobile:
                        buttons = self.driver.find_elements(By.XPATH, "//a[@role='button' or contains(@data-sigil, 'touchable')]")
                    else:
                        buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']")
                    
                    logger.info(f"Botones encontrados: {len(buttons)}")
                    
                    for btn in buttons:
                        try:
                            # Verificar si el botón es visible
                            if not self.is_element_visible(btn):
                                continue
                                
                            aria_label = btn.get_attribute("aria-label")
                            if aria_label and ("me gusta" in aria_label.lower() or "like" in aria_label.lower()):
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.info(f"Clic en botón con aria-label: {aria_label}")
                                
                                # Registrar actividad
                                self.save_activity_log("like", post_url, "success")
                                return True
                        except:
                            continue
                except Exception as e:
                    logger.error(f"Error en método alternativo de like: {e}")
            
            logger.error("No se pudo encontrar ningún botón de like")
            return False
            
        except Exception as e:
            logger.error(f"Error al dar like a la publicación: {e}")
            self.save_activity_log("like", post_url, "error", str(e))
            return False
    
    def comment_post_in_current_view(self, post_url, comment=None):
        """Comenta en la publicación que está actualmente en vista (después de find_specific_post)"""
        if not self.connected:
            if not self.login():
                return False
        
        if not comment:
            # Filtrar comentarios que contengan emojis para evitar errores de codificación
            text_comments = [c for c in self.comment_templates["general"] 
                          if not any(ord(char) > 127 for char in c)]
            
            if text_comments:
                comment = random.choice(text_comments)
            else:
                comment = "Muy interesante!"
        
        try:
            logger.info(f"Comentando en la publicación actualmente en vista")
            # Registrar el comentario de forma segura evitando problemas de codificación
            try:
                safe_comment = comment.encode('ascii', 'replace').decode('ascii')
                logger.info(f"Comentario: {safe_comment}")
            except:
                logger.info("Comentario con caracteres especiales seleccionado")
            
            # Detectar si estamos en la versión móvil
            is_mobile = "m.facebook.com" in self.driver.current_url
            
            # Desplazarse un poco más abajo para ver la sección de comentarios
            self.driver.execute_script("window.scrollBy(0, 200);")
            time.sleep(2)
            
            # Tomar captura para depuración
            try:
                screenshot_path = f"logs/before_comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Captura antes de comentar guardada en {screenshot_path}")
            except:
                pass
            
            if is_mobile:
                # Versión móvil
                # Primero, buscar y hacer clic en el botón de comentario en móvil
                mobile_comment_buttons = [
                    "//a[contains(text(), 'Comentar') or contains(text(), 'Comment')]",
                    "//span[contains(text(), 'Comentar') or contains(text(), 'Comment')]",
                    "//a[starts-with(@data-sigil, 'feed-ufi-focus')]",
                    "//a[contains(@data-uri, 'comment')]",
                    "//a[contains(@aria-label, 'comentar') or contains(@aria-label, 'comment')]"
                ]
                
                for selector in mobile_comment_buttons:
                    try:
                        comment_buttons = self.driver.find_elements(By.XPATH, selector)
                        for btn in comment_buttons:
                            if self.is_element_visible(btn):
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.info(f"Botón comentar móvil encontrado y clicado: {selector}")
                                time.sleep(3)
                                break
                    except:
                        continue
                
                # Buscar el área de texto para comentarios en móvil
                mobile_textareas = [
                    "//textarea[@id='composerInput']",
                    "//textarea[contains(@placeholder, 'coment') or contains(@placeholder, 'Comment')]",
                    "//textarea[@name='comment_text']",
                    "//textarea[contains(@id, 'comment')]",
                    "//textarea"
                ]
                
                for selector in mobile_textareas:
                    try:
                        textareas = self.driver.find_elements(By.XPATH, selector)
                        for textarea in textareas:
                            if self.is_element_visible(textarea):
                                # Intentar interactuar con el textarea
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", textarea)
                                time.sleep(1)
                                textarea.click()
                                time.sleep(1)
                                
                                # Limpiar y enviar texto
                                try:
                                    textarea.clear()
                                    time.sleep(0.5)
                                except:
                                    pass
                                
                                textarea.send_keys(comment)
                                time.sleep(2)
                                
                                # Buscar y hacer clic en el botón de publicar
                                post_buttons = [
                                    "//input[@type='submit']",
                                    "//button[@type='submit']",
                                    "//button[contains(text(), 'Publicar') or contains(text(), 'Post')]",
                                    "//button[@value='Post']",
                                    "//button[contains(@data-sigil, 'submit')]"
                                ]
                                
                                button_clicked = False
                                for btn_selector in post_buttons:
                                    try:
                                        submit_buttons = self.driver.find_elements(By.XPATH, btn_selector)
                                        for submit_btn in submit_buttons:
                                            if self.is_element_visible(submit_btn):
                                                self.driver.execute_script("arguments[0].click();", submit_btn)
                                                logger.info(f"Botón publicar encontrado y clicado: {btn_selector}")
                                                button_clicked = True
                                                time.sleep(3)
                                                break
                                    except:
                                        continue
                                
                                if not button_clicked:
                                    # Si no se encontró botón, intentar con Enter
                                    textarea.send_keys(Keys.ENTER)
                                    logger.info("Enviado comentario con tecla Enter")
                                    time.sleep(3)
                                
                                # Registrar actividad
                                self.save_activity_log("comment", post_url, "success", {"comment": comment})
                                return True
                    except Exception as e:
                        logger.debug(f"Error con textarea móvil {selector}: {str(e)}")
                        continue
                    
            else:
                # Versión de escritorio
                # Primero, buscar y hacer clic en el botón "Comentar" si existe
                comment_button_selectors = [
                    "//span[text()='Comentar' or text()='Comment']/ancestor::div[@role='button']",
                    "//div[@aria-label='Comentar' or @aria-label='Comment']",
                    "//a[@aria-label='Comentar' or @aria-label='Comment']"
                ]
                
                for selector in comment_button_selectors:
                    try:
                        comment_buttons = self.driver.find_elements(By.XPATH, selector)
                        for btn in comment_buttons:
                            if self.is_element_visible(btn):
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.info("Botón de comentar encontrado y clicado")
                                time.sleep(2)
                                break
                    except:
                        continue
                
                # Actualizar selectores para encontrar el área de comentarios
                comment_selectors = [
                    # Más específicos primero
                    "//div[@aria-label='Escribe un comentario...' or @aria-label='Write a comment...']",
                    "//div[@contenteditable='true' and @role='textbox']",
                    "//form[@role='presentation']//div[@contenteditable='true']",
                    # Buscar por placeholder también
                    "//div[@data-placeholder='Escribe un comentario...' or @data-placeholder='Write a comment...']",
                    # Buscar la sección de comentarios primero y luego el área de texto
                    "//div[contains(@aria-label, 'comentario') or contains(@aria-label, 'comment')]"
                ]
                
                # Ahora buscar el área de comentario
                for selector in comment_selectors:
                    try:
                        comment_areas = self.driver.find_elements(By.XPATH, selector)
                        for comment_area in comment_areas:
                            if self.is_element_visible(comment_area):
                                # Scroll y clic
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_area)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", comment_area)
                                time.sleep(1)
                                
                                # Intentar limpiar el área primero
                                try:
                                    comment_area.clear()
                                except:
                                    pass
                                
                                # Usar JavaScript para establecer el valor
                                self.driver.execute_script("arguments[0].textContent = arguments[1];", comment_area, comment)
                                time.sleep(1)
                                
                                # Método alternativo: enviar teclas
                                comment_area.send_keys(comment)
                                time.sleep(2)
                                
                                # Enviar con Enter
                                comment_area.send_keys(Keys.ENTER)
                                time.sleep(3)
                                
                                # Registrar actividad
                                self.save_activity_log("comment", post_url, "success", {"comment": comment})
                                logger.info(f"Comentario enviado exitosamente: {comment}")
                                return True
                    except Exception as e:
                        logger.debug(f"Error con selector {selector}: {e}")
                        continue
            
            # Si ninguno de los métodos funcionó, intentar un enfoque genérico
            logger.warning("Intentando método alternativo para encontrar el área de comentario")
            try:
                # Buscar todos los elementos editables visibles
                if is_mobile:
                    potential_elements = self.driver.find_elements(By.XPATH, "//textarea | //input[@type='text']")
                else:
                    potential_elements = self.driver.find_elements(By.XPATH, "//div[@contenteditable='true'] | //div[@role='textbox']")
                
                logger.info(f"Elementos potenciales encontrados: {len(potential_elements)}")
                
                for element in potential_elements:
                    try:
                        if not self.is_element_visible(element):
                            continue
                            
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(1)
                        
                        # Probar si podemos escribir
                        element.send_keys(comment)
                        time.sleep(1)
                        element.send_keys(Keys.ENTER)
                        time.sleep(3)
                        
                        logger.info("Comentario posiblemente enviado con elemento alternativo")
                        self.save_activity_log("comment", post_url, "success", {"comment": comment})
                        return True
                    except:
                        continue
            except Exception as e:
                logger.error(f"Error en método alternativo final: {e}")
            
            # Tomar captura de pantalla final para depuración
            try:
                screenshot_path = f"logs/comment_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Captura de error guardada en {screenshot_path}")
            except:
                pass
            
            logger.error("No se pudo encontrar el área de comentario")
            return False
            
        except Exception as e:
            logger.error(f"Error comentando en la publicación: {e}")
            self.save_activity_log("comment", post_url, "error", str(e))
            return False
    
    def interact_with_post(self, post_url, like=True, comment=True, share=False):
        """Interactúa con una publicación específica (like, comentario, compartir)"""
        if not self.connected:
            if not self.login():
                return False
        
        success = True
        
        # No convertir URLs móviles, usar la URL exactamente como se proporciona
        original_url = post_url

        # Comprobar si la URL contiene identificadores importantes
        url_parts = original_url.split('/')
        post_id = None
        
        for part in url_parts:
            if part.startswith('pfbid'):
                post_id = part
                logger.info(f"ID de publicación detectado: {post_id}")
                break
        
        # Navegar a la URL de la publicación
        logger.info(f"Navegando a la URL exacta proporcionada: {original_url}")
        self.driver.get(original_url)
        time.sleep(5)
        
        # NUEVO: Identificar la publicación específica antes de interactuar
        post_found = self.find_specific_post(original_url)
        
        if not post_found:
            logger.warning("No se pudo identificar la publicación específica, pero se continuará intentando interactuar")
        
        # Verificar si la redirección ocurrió
        current_url = self.driver.current_url
        if post_id and post_id not in current_url:
            logger.warning(f"¡ALERTA! Posible redirección detectada. URL original: {original_url}")
            logger.warning(f"URL actual: {current_url}")
            logger.warning("Intentando volver a la URL original...")
            
            # Intento 1: Usar la URL original de nuevo
            self.driver.get(original_url)
            time.sleep(5)
            
            # Intentar identificar de nuevo
            post_found = self.find_specific_post(original_url)
            
            if not post_found:
                logger.warning("No se pudo identificar la publicación después del reintento")
        
        # Dar like si se solicita
        if like:
            like_success = self.like_post_in_current_view(original_url)  # Nuevo método para dar like a la publicación actual
            if not like_success:
                success = False
        
        # Comentar si se solicita
        if comment:
            comment_success = self.comment_post_in_current_view(original_url)  # Nuevo método para comentar en la publicación actual
            if not comment_success:
                success = False
        
        # Compartir si se solicita
        if share:
            share_success = self.share_post(original_url)  # Usar la URL original
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