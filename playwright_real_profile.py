import asyncio
import os
import random
import csv
from playwright.async_api import async_playwright
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Directorio para guardar la sesión (cookies, localStorage, etc.)
USER_DATA_DIR = './fb_session'

# URL del post a scrapear
POST_URL = "https://www.facebook.com/100064865195272/posts/1355079436664217/?mibextid=rS40aB7S9Ucbxw6v"

async def main():
    # Nos aseguramos de que el directorio de sesión exista
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    async with async_playwright() as p:
        logging.info(f"Lanzando navegador con contexto persistente en: {USER_DATA_DIR}")
        
        # Argumentos para evasión de detección
        args = [
            '--disable-blink-features=AutomationControlled',
            '--start-maximized',  # Iniciar maximizado para ver mejor
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-infobars',
            '--window-position=0,0',
            '--ignore-certifcate-errors',
            '--ignore-certifcate-errors-spki-list',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        # Lanzamos el contexto persistente
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,  # Requerido: headless=False
            args=args,
            viewport={'width': 1280, 'height': 720}, # O null para max
            # slow_mo=50, # Opcional: para ver qué hace
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Evasión extra de detección mediante scripts en la página
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        logging.info(f"Navegando a {POST_URL}")
        await page.goto(POST_URL, timeout=60000)

        # Mecanismo de espera para Login Manual
        # Buscamos un elemento que indique que estamos logueados, por ejemplo el icono de cuenta.
        # El selector puede variar, pero generalmente hay un div con role='navigation' o aria-label='Account'
        logging.info("Verificando estado de la sesión...")
        
        try:
            # Intentamos esperar por un elemento típico de usuario logueado.
            # Ajusta este selector si FB lo cambia. 'div[role="navigation"]' suele estar en la barra superior.
            # O busca el input de login para saber si NO estamos logueados.
            await page.wait_for_selector('div[role="navigation"]', timeout=5000)
            logging.info("Sesión detectada iniciada.")
        except:
            logging.warning("No se detectó sesión iniciada automáticamente.")
            logging.info("POR FAVOR: Inicia sesión manualmente en la ventana del navegador.")
            logging.info("El script esperará hasta que detecte que has iniciado sesión (esperando barra de navegación)...")
            
            # Espera larga o loop hasta detectar login
            try:
                # Damos 120 segundos para que el usuario se loguee
                await page.wait_for_selector('div[role="navigation"]', timeout=120000)
                logging.info("Login detectado exitosamente.")
            except:
                logging.error("Tiempo de espera de login agotado. Intenta correr el script de nuevo y loguearte más rápido.")
                await context.close()
                return

        logging.info("Esperando a que cargue el post completamente...")
        await asyncio.sleep(5) # Espera inicial
        
        # --- SECCIÓN CRÍTICA: Cambiar a "Todos los comentarios" ---
        logging.info("Configurando filtro: 'Todos los comentarios'...")
        try:
            filter_button = page.locator('div[role="button"]:has-text("relevante"), div[role="button"]:has-text("relevant"), div[role="button"]:has-text("reciente"), div[role="button"]:has-text("recent")')
            
            if await filter_button.count() > 0:
                await filter_button.first.click()
                await asyncio.sleep(2)
                import re
                all_comments_option = page.locator('div[role="menuitem"], div[role="option"], span').filter(has_text=re.compile(r"^Todos los comentarios$|^All comments$", re.IGNORECASE))
                
                if await all_comments_option.count() > 0:
                    await all_comments_option.first.click()
                    logging.info("Filtro 'Todos los comentarios' seleccionado.")
                    await asyncio.sleep(5)
        except Exception as e:
            logging.warning(f"Error al cambiar filtro: {e}")

        # --- EXTRACCIÓN PROGRESIVA ---
        extracted_data = []
        seen_comments = set()
        csv_file = 'comentarios_fb.csv'

        async def extract_and_save():
            nonlocal extracted_data, seen_comments
            try:
                elements = await page.locator('div[role="article"]').all()
                new_found = 0
                for el in elements:
                    try:
                        text_nodes = el.locator('div[dir="auto"], span[dir="auto"]')
                        node_count = await text_nodes.count()
                        parts = []
                        for i in range(node_count):
                            content = await text_nodes.nth(i).text_content()
                            if content: parts.append(content.strip())
                        
                        if len(parts) >= 2:
                            author = parts[0]
                            # Buscamos la parte que probablemente sea el comentario (más larga)
                            comment_body = max(parts[1:], key=len)
                            unique_key = f"{author}_{comment_body}"
                            
                            if unique_key not in seen_comments:
                                extracted_data.append({
                                    '#': len(extracted_data) + 1,
                                    'Autor': author,
                                    'Comentario': comment_body
                                })
                                seen_comments.add(unique_key)
                                new_found += 1
                    except: continue
                
                if new_found > 0:
                    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.DictWriter(f, fieldnames=['#', 'Autor', 'Comentario'])
                        writer.writeheader()
                        writer.writerows(extracted_data)
                    logging.info(f"PROGRESO: {len(extracted_data)} comentarios guardados (Nuevos: {new_found})")
            except Exception as e:
                logging.error(f"Error en extracción progresiva: {e}")

        # Lógica de Scroll y Carga de Comentarios (MODO ENGAÑO + PROGRESIVO)
        logging.info("Iniciando carga profunda con guardado progresivo...")
        last_found_count = 0
        no_change_count = 0
        total_actions = 0
        
        while True:
            total_actions += 1
            logging.info(f"Acción {total_actions} - Buscando más comentarios...")
            
            # Extraer lo que hay hasta ahora
            await extract_and_save()
            
            current_count = len(extracted_data)
            if current_count > last_found_count:
                last_found_count = current_count
                no_change_count = 0
            else:
                no_change_count += 1

            # 1. Scroll al fondo con pausas aleatorias
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(2, 4))
            
            # 2. Expandir "Ver más" (varias etiquetas posibles)
            try:
                # Selectores más amplios para botones de carga
                more_selectors = [
                    "text=/Ver\\s.*comentarios/i", 
                    "text=/View\\s.*comments/i", 
                    "text=/anteriores/i", 
                    "text=/previous/i",
                    "div[role='button']:has-text('más')",
                    "div[role='button']:has-text('more')"
                ]
                for sel in more_selectors:
                    buttons = page.locator(sel)
                    b_count = await buttons.count()
                    for i in range(b_count):
                        try:
                            btn = buttons.nth(i)
                            if await btn.is_visible():
                                await btn.click(timeout=2000)
                                await asyncio.sleep(1)
                        except: continue
            except: pass

            # 3. Expandir hilos (respuestas)
            try:
                replies_locator = page.locator("text=/\\d+\\s(respuestas?|replies?)/i")
                r_count = await replies_locator.count()
                # Expandimos de a poco para no saturar
                for i in range(min(r_count, 20)):
                    try:
                        btn = replies_locator.nth(i)
                        if await btn.is_visible():
                            # Verificar si ya está expandido (a veces el texto cambia)
                            await btn.click(timeout=2000)
                            await asyncio.sleep(0.5)
                    except: continue
            except: pass

            # 4. Movimiento "Humano" (scroll arriba/abajo)
            if total_actions % 5 == 0:
                logging.info("Realizando scroll de refresco para despertar carga lenta...")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
                await asyncio.sleep(1)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            # Criterio de parada: Si después de 15 acciones no hay nuevos comentarios
            if no_change_count >= 15: 
                logging.info("Parece que ya no hay más comentarios nuevos para cargar.")
                break
            
            if total_actions > 400: break # Límite de seguridad

        logging.info(f"Scraping finalizado. Total: {len(extracted_data)}")
        await context.close()

if __name__ == '__main__':
    asyncio.run(main())
