import os
import pandas as pd
import requests
import json
import time
import hashlib
import logging
import argparse
from typing import List, Dict, Any, Optional

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TopicClassifier:
    TOPICS = [
        "Vocación Médica y Humanidad",
        "Legalidad y Compatibilidad Funcional",
        "Rechazo a la denuncia",
        "Crítica Política y Valores Políticos",
        "No identificado"
    ]

    SYSTEM_PROMPT = """Eres un experto en análisis de discurso político uruguayo. Tu tarea es analizar comentarios de Facebook sobre una denuncia JUTEP contra el intendente Daniel Ximénez (médico) por parte de Carol Aviaga.
Devuelve SOLO un JSON válido con la clasificación del tópico. No incluyas explicaciones ni markdown.

Tópicos permitidos:
1) Vocación Médica y Humanidad: Enfocado en su rol de médico, salvar vidas, ética profesional, humanidad, sanatorios. Palabras clave: doctor, cirujano, pacientes, vida.
2) Legalidad y Compatibilidad Funcional: Enfocado en la ley, la constitución, si es legal o no trabajar en dos lugares, reglamentos. Palabras clave: constitución, ley, permitido, municipal, privado.
3) Rechazo a la denuncia: Enfocado en criticar la denuncia misma, verla como "política barata", "circo", "oportunismo", pedir que lo dejen trabajar. Palabras clave: dejen trabajar, al pedo, política, joder, resentimiento.
4) Crítica Política y Valores Políticos: Enfocado en críticas más generales a la gestión, valores éticos de la política en general, o ataques directos a figuras políticas sin centrarse solo en la denuncia.
5) No identificado: Úsalo solo cuando el comentario sea demasiado corto, irrelevante, o no contenga información suficiente para asignarlo a ninguno de los tópicos anteriores.

Estructura de respuesta JSON:
{
  "topic": "<UNO de los 5 topics con el nombre exacto>"
}
"""

    def __init__(self, model: str, host: str, sleep_time: float, cache_file: str):
        self.model = model
        self.host = host.rstrip('/')
        self.sleep_time = sleep_time
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error cargando cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error guardando cache: {e}")

    def get_text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _call_ollama(self, prompt: str, correction: bool = False) -> Optional[Dict[str, Any]]:
        url = f"{self.host}/api/generate"
        full_prompt = f"{self.SYSTEM_PROMPT}\n\nTexto a clasificar:\n\"{prompt}\""
        if correction:
            full_prompt += "\n\nAVISO: Tu respuesta anterior no fue un JSON válido o contenía tópicos inválidos. Por favor, asegúrate de usar SOLO los tópicos de la lista y formato JSON estricto."

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            data = json.loads(result.get("response", "{}"))
            
            # Validar tópico
            topic = data.get("topic")
            if topic not in self.TOPICS:
                return None
            return topic
        except (requests.exceptions.RequestException, json.JSONDecodeError, Exception) as e:
            logging.error(f"Error en llamada a Ollama: {e}")
            return None

    def classify(self, text: str) -> str:
        text_hash = self.get_text_hash(text)
        if text_hash in self.cache:
            return self.cache[text_hash]

        # Pre-check: si el comentario es demasiado corto
        if len(text.strip()) < 10:
            result = "No identificado"
            self.cache[text_hash] = result
            return result

        # Intento 1
        result = self._call_ollama(text)
        
        # Intento 2 (Corrección)
        if not result:
            logging.warning(f"Reintentando clasificación para: {text[:50]}...")
            result = self._call_ollama(text, correction=True)

        # Fallback
        if not result:
            logging.error(f"Fallo total en clasificación. Aplicando fallback para: {text[:50]}...")
            medical_keywords = ['médico', 'doctor', 'paciente', 'salv', 'vida', 'human', 'curar']
            is_medical = any(word in text.lower() for word in medical_keywords)
            result = "Vocación Médica y Humanidad" if is_medical else "No identificado"

        self.cache[text_hash] = result
        time.sleep(self.sleep_time)
        return result

def detect_comment_column(df: pd.DataFrame) -> str:
    candidates = ["Comentario", "comment", "texto", "text", "body"]
    for cand in candidates:
        if cand in df.columns:
            return cand
    # Heurística: columna con cadenas más largas
    str_cols = df.select_dtypes(include=['object']).columns
    if len(str_cols) > 0:
        return max(str_cols, key=lambda c: df[c].astype(str).str.len().mean())
    raise ValueError("No se pudo detectar la columna de comentarios.")

def main():
    parser = argparse.ArgumentParser(description="Detección de tópicos usando Ollama")
    parser.add_argument("--input", default="Analítica_Datos_Daniel_Carol.csv", help="CSV de entrada")
    parser.add_argument("--output", default="Topics_Clean.csv", help="CSV de salida")
    parser.add_argument("--model", default="gpt-oss:120b-cloud", help="Modelo de Ollama")
    parser.add_argument("--host", default="http://localhost:11434", help="Host de Ollama API")
    parser.add_argument("--sleep", type=float, default=0.2, help="Tiempo de espera entre llamadas")
    parser.add_argument("--checkpoint_every", type=int, default=10, help="Guardar cada N comentarios")
    parser.add_argument("--cache_file", default="topics_cache.json", help="Archivo de cache")
    
    args = parser.parse_args()

    # Cargar datos
    if not os.path.exists(args.input):
        logging.error(f"Archivo de entrada no encontrado: {args.input}")
        return

    df = pd.read_csv(args.input)
    comment_col = detect_comment_column(df)
    logging.info(f"Usando columna de comentarios: '{comment_col}'")

    classifier = TopicClassifier(args.model, args.host, args.sleep, args.cache_file)

    # Preparar columna nueva si no existe
    if "Topic" not in df.columns:
        df["Topic"] = None

    total = len(df)
    start_time = time.time()

    logging.info(f"Iniciando procesamiento de {total} comentarios...")

    for i, row in df.iterrows():
        # Saltar si ya está procesado y tiene datos válidos
        if pd.notnull(row["Topic"]) and classifier.get_text_hash(str(row[comment_col])) in classifier.cache:
            continue

        comment = str(row[comment_col])
        topic = classifier.classify(comment)

        df.at[i, "Topic"] = topic

        # Checkpoint e informe de progreso
        if (i + 1) % args.checkpoint_every == 0 or (i + 1) == total:
            df.to_csv(args.output, index=False, encoding='utf-8-sig')
            classifier._save_cache()
            
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            remaining = (total - (i + 1)) * avg_time
            logging.info(f"Progreso: {i+1}/{total} | Tiempo est. restante: {remaining/60:.2f} min")

    logging.info(f"Procesamiento completado. Resultados guardados en: {args.output}")

if __name__ == "__main__":
    main()
