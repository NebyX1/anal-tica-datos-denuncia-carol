"""
Script: classify_apoyo.py
Descripción: Clasifica comentarios de Facebook usando Ollama local y exporta a CSV.
Ejecución:
    1. Instalar dependencias: pip install -r requirements.txt
    2. Configurar .env basado en .env.example
    3. Ejecutar: python classify_apoyo.py
"""

import os
import csv
import json
import time
import re
import logging
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_config() -> Dict[str, Any]:
    load_dotenv()
    # Contexto manual incrustado según solicitud
    contexto_manual = "Clasificás postura hacia Daniel Ximénez por la denuncia JUTEP (médico siendo intendente). Elegí una etiqueta: FAVORABLE si el comentario justifica o defiende que trabaje (legalidad, ‘no lo impide’, ‘mientras cumpla’, ‘no jodan’, ‘déjenlo’, ‘no hay problema’, ‘la ley permite’, ‘mutualista privada’, ‘no depende de la intendencia’, ‘no hace negocios con la intendencia’), si lo elogia por ayudar/salvar vidas o usar conocimientos (‘admira’, ‘salud de las personas’, ‘salvar vidas’), si critica a la denunciante/oposición o el ‘fanatismo’, o si usa comparación para justificar (‘cuando Tabaré Vázquez…’, ‘otros intendentes trabajaban’). CONTRARIO si apoya la denuncia o reclama ética/incompatibilidad/ilegalidad/conflicto de intereses (‘ética’, ‘denunciar’, ‘incompatible’, ‘ilegal’, ‘conflicto’, ‘corrupción’, ‘que lo investiguen’, ‘renuncie’, ‘sanción’). NEUTRAL solo si no hay postura sobre Ximénez. Regla fuerte: si el texto contiene cualquier justificación o defensa (legalidad, comparación, “dejar trabajar”, “salvar vidas”, “omisión de asistencia”) => FAVORABLE."

    return {
        "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud"),
        "CLASSIFIER_CONTEXT": contexto_manual,
        "BATCH_SIZE": int(os.getenv("BATCH_SIZE", "5")),
        "TEMPERATURE": float(os.getenv("TEMPERATURE", "0.0")),
        "TOP_P": float(os.getenv("TOP_P", "0.9")),
        "INPUT_CSV": os.getenv("INPUT_CSV", "input.csv"),
        "OUTPUT_CSV": os.getenv("OUTPUT_CSV", "Analítica_Datos_Daniel_Carol.csv"),
        "COMMENT_COLUMN": os.getenv("COMMENT_COLUMN", "Comentario"),
        "ID_COLUMN": os.getenv("ID_COLUMN", "#"),
        "APOYO_COLUMN": os.getenv("APOYO_COLUMN", "Apoyo Daniel"),
        "SLEEP_MS": int(os.getenv("SLEEP_BETWEEN_BATCHES_MS", "200")),
        "TIMEOUT": 180,
    }


def extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Extrae un JSON array de manera robusta sin regex codicioso."""
    if not text:
        return []

    cleaned = text.strip()
    # a) json.loads directo si parece array completo
    if cleaned.startswith("[") and cleaned.endswith("]"):
        try:
            return json.loads(cleaned)
        except Exception:
            pass

    # b) substring entre primer '[' y ultimo ']'
    try:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start : end + 1]
            return json.loads(candidate)
    except Exception:
        pass

    # c) regex no codicioso con multiples objetos
    try:
        match = re.search(r"\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*\]", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        logging.error(f"Error parseando JSON con regex: {e}")

    return []


def call_ollama(
    config: Dict[str, Any], messages: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """Llamada a Ollama con reintentos y backoff exponencial."""
    url = f"{config['OLLAMA_HOST']}/api/chat"
    payload = {
        "model": config["OLLAMA_MODEL"],
        "messages": messages,
        "stream": False,
        "options": {"temperature": config["TEMPERATURE"], "top_p": config["TOP_P"]},
    }

    retries = 3
    for i in range(retries):
        try:
            response = requests.post(url, json=payload, timeout=config["TIMEOUT"])
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")

            results = extract_json_array(content)
            if results:
                return results

            # Si no hay array, intentar parsear directamente por si es JSON puro
            try:
                return json.loads(content)
            except:
                pass
        except (requests.exceptions.RequestException, Exception) as e:
            wait_time = 2**i
            logging.warning(
                f"Error en intento {i+1}/{retries}: {e}. Reintentando en {wait_time}s..."
            )
            time.sleep(wait_time)

    return []


def classify_batch(
    config: Dict[str, Any], batch: List[Dict[str, str]]
) -> Dict[str, str]:
    """Prepara el batch y llama al modelo para obtener las clasificaciones."""
    system_msg = config["CLASSIFIER_CONTEXT"]

    user_msg = (
        "Devolvé SOLO JSON válido, sin texto extra.\n"
        'Formato: [{"id":"<id>","apoyo":"FAVORABLE|CONTRARIO|NEUTRAL"}, ...]\n'
        "Evitá NEUTRAL: usalo SOLO si el comentario no tiene postura sobre Ximénez. Si hay defensa/justificación aunque sea indirecta => FAVORABLE.\n\n"
        "Comentarios:\n"
    )

    for item in batch:
        user_msg += f"- ID: {item['id']}, Comentario: {item['text']}\n"

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    raw_results = call_ollama(config, messages)

    # Mapear resultados por ID para fácil acceso
    classified_data: Dict[str, str] = {}
    valid_labels = {"FAVORABLE", "CONTRARIO", "NEUTRAL"}
    for res in raw_results:
        if "id" in res and "apoyo" in res:
            res_id = str(res["id"]).strip()
            apoyo = str(res["apoyo"]).strip().upper()
            if apoyo in valid_labels:
                classified_data[res_id] = apoyo

    return classified_data


def main():
    config = load_config()
    if not config["CLASSIFIER_CONTEXT"]:
        logging.error("CLASSIFIER_CONTEXT es obligatorio en el .env")
        return

    if not os.path.exists(config["INPUT_CSV"]):
        logging.error(f"No se encuentra el archivo de entrada: {config['INPUT_CSV']}")
        return

    rows = []
    with open(config["INPUT_CSV"], mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if config["APOYO_COLUMN"] not in fieldnames:
            fieldnames.append(config["APOYO_COLUMN"])

        for idx, row in enumerate(reader):
            # Obtener ID estable
            row_id = row.get(config["ID_COLUMN"], str(idx))
            row["__internal_id__"] = row_id  # Guardamos para el batch
            rows.append(row)

    total = len(rows)
    logging.info(f"Total de filas a procesar: {total}")

    batch_size = config["BATCH_SIZE"]
    processed_count = 0

    with open(config["OUTPUT_CSV"], mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(0, total, batch_size):
            current_batch_rows = rows[i : i + batch_size]
            batch_payload = [
                {"id": r["__internal_id__"], "text": r[config["COMMENT_COLUMN"]]}
                for r in current_batch_rows
            ]

            logging.info(
                f"Procesando batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}..."
            )

            classified_map = classify_batch(config, batch_payload)
            logging.info(
                f"Clasificados en este batch: {len(classified_map)}/{len(current_batch_rows)}"
            )
            if len(classified_map) == 0:
                logging.warning(
                    "Batch sin clasificaciones validas; usando fallback NEUTRAL."
                )

            for row in current_batch_rows:
                # Buscar en el mapa, si no está o falla, poner NEUTRAL
                internal_id = str(row["__internal_id__"]).strip()
                row[config["APOYO_COLUMN"]] = classified_map.get(internal_id, "NEUTRAL")

                # Limpiar columna interna antes de escribir
                del row["__internal_id__"]
                writer.writerow(row)

            processed_count += len(current_batch_rows)
            time.sleep(config["SLEEP_MS"] / 1000.0)

    logging.info(f"Procesamiento finalizado. {processed_count} filas procesadas.")
    logging.info(f"Archivo generado en: {os.path.abspath(config['OUTPUT_CSV'])}")


if __name__ == "__main__":
    main()
