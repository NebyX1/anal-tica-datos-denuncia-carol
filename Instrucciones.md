# Guía de Uso: Sentiment Analytics - Caso Lavalleja

Este proyecto permite extraer comentarios de Facebook, limpiarlos, clasificarlos mediante modelos de lenguaje (LLMs) locales/cloud a través de Ollama y generar visualizaciones de datos.

---

## 1. Requisitos Previos e Instalación

### Ollama
1.  **Instalación**: Descarga e instala [Ollama](https://ollama.com/) como servidor local.
2.  **Cuenta y Modelo**: Crea tu cuenta y asegúrate de descargar el manifiesto del modelo cloud seleccionado. En este caso, el proyecto utiliza por defecto `gpt-oss:120b-cloud`
3.  **Servidor**: El servidor de Ollama debe estar **abierto y corriendo** durante todo el proceso de análisis de sentimientos.

### Entorno de Python
1.  **Crear Entorno Virtual**:
    ```powershell
    python -m venv venv
    ```
2.  **Activar Entorno**:
    *   Windows: `.\venv\Scripts\activate`
    *   Linux/Mac: `source venv/bin/activate`
3.  **Instalar Librerías**:
    ```powershell
    pip install -r requirements.txt
    ```

---

## 2. Paso 1: Extracción de Datos (Scraping)

El script `playwright_real_profile.py` utiliza un perfil real de Chrome para evitar bloqueos.

1.  **Primera Ejecución (Autenticación)**:
    Ejecuta el script: `python playwright_real_profile.py`.
    Se abrirá una instancia de Chrome controlada. **Debes iniciar sesión manualmente en tu cuenta de Facebook**. Los datos se guardarán localmente en la carpeta `user_data`, por lo que solo es necesario hacerlo la primera vez.
    *Nota: Esto es seguro en computadoras personales, pero no se recomienda en equipos compartidos.*

2.  **Segunda Ejecución (Scraping)**:
    Una vez logueado, corre el script nuevamente. Empezará a extraer los comentarios automáticamente hacia un archivo CSV (ej. `comentarios_fb.csv`).

---

## 3. Paso 2: Limpieza de Datos

Para eliminar redundancias y comentarios repetidos:
1.  Ejecuta el script de limpieza:
    ```powershell
    python clean_duplicates.py
    ```
    Esto generará un archivo limpio (ej. `comentarios_fb_limpios.csv` o `Comentarios_Limpios.csv`).

---

## 4. Paso 3: Análisis de Sentimientos (Clasificación)

Este paso requiere que Ollama esté activo y el modelo cargado.

1.  **Clasificación Daniel Ximénez**:
    Usa el script para etiquetar la postura hacia el intendente:
    ```powershell
    python classify_apoyo.py
    ```
    Clasificará los comentarios como `FAVORABLE`, `CONTRARIO` o `NEUTRAL`.

2.  **Clasificación Carol Aviaga**:
    Usa el script específico para la edil:
    ```powershell
    python classify_apoyo_carol.py
    ```

Los resultados se consolidarán en el archivo de analítica final (ej. `Analítica_Datos_Daniel_Carol.csv`).

---

## 5. Paso 4: Visualización

Una vez que los datos están etiquetados, puedes generar los informes visuales:

1.  **Nube de Palabras**:
    ```powershell
    python wordcloud_gen.py
    ```
    Genera una imagen con los términos más frecuentes.
    *Advertencia: Este script no contempla la limpieza de nombres de usuarios mencionados en respuestas (etiquetas). Si los comentarios incluyen menciones tipo "Juan Perez", estos nombres aparecerán en la nube. Esa limpieza se realizó previamente con un script externo no incluido en este paquete.*

2.  **Gráficos de Torta**:
    ```powershell
    python plot_apoyo_pies.py
    ```
    Crea un archivo `apoyo_pie_charts.png` con la distribución de posturas para ambos protagonistas.

---

## Notas Importantes
*   **Configuración**: Puedes ajustar los modelos, rutas de archivos y nombres de columnas en el archivo `.env` (basándote en `example.env`).
*   **Limpieza de Texto**: La precisión del análisis de sentimientos y la nube de palabras depende de la calidad del texto. Asegúrate de que el CSV de entrada tenga las columnas correctamente nombradas en el archivo de configuración.
