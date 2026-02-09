"""
Script: classify_apoyo_carol.py
Descripción: Clasifica la postura hacia Carol Aviaga usando Ollama local y exporta a CSV.
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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config() -> Dict[str, Any]:
    load_dotenv()
    # Contexto manual incrustado para análisis exclusivo de Carol Aviaga
    contexto_manual = (
        "Clasificás comentarios de Facebook sobre la denuncia de Carol Aviaga (edil) contra el intendente Daniel Ximénez ante JUTEP. "
        "Tu única tarea es etiquetar la postura del comentario hacia Carol Aviaga con: FAVORABLE, CONTRARIO o NEUTRAL. "
        "CONTRARIO si el comentario ataca a Carol, la desacredita o la insulta (ej. ‘envidiosa’, ‘busca cámara’, ‘resentida’, ‘loca’, ‘ignorante’, ‘no tiene nada que hacer’), "
        "si hay burlas o desprecio por ser mujer (misoginia, sexualización, ‘andá a la cocina’, ‘histérica’), si la acusa de mala fe, politiquería, persecución, mentir, operar, difamar, "
        "o si dice que su denuncia es un circo/invento. También es CONTRARIO si el comentario defiende a Ximénez atacando a Carol (ej. ‘dejalo trabajar’, ‘no lo impide’, ‘qué jode’, ‘aprendé la ley’, ‘informate’) "
        "cuando el blanco principal es Carol o su denuncia. FAVORABLE solo si el comentario expresa apoyo explícito a Carol como persona o a su denuncia (aprobación clara sin ironía). "
        "NEUTRAL si no expresa una postura hacia Carol (habla de leyes en abstracto, de Ximénez sin mencionar a Carol, o es ambiguo). "
        "Regla: si hay cualquier descalificación o insulto hacia Carol o hacia ‘la mujer/la edil/la denunciante’, clasificá CONTRARIO. "
        "Salida: devolvé SOLO JSON válido con el campo ‘apoyo’ usando estas etiquetas."
    )
    
    return {
        "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip('/'),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud"),
        "CLASSIFIER_CONTEXT": contexto_manual,
        "BATCH_SIZE": int(os.getenv("BATCH_SIZE", "5")),
        "TEMPERATURE": float(os.getenv("TEMPERATURE", "0.0")),
        "TOP_P": float(os.getenv("TOP_P", "0.9")),
        "INPUT_CSV": os.getenv("INPUT_CSV", "Comentarios_Limpios.csv"),
        "OUTPUT_CSV": os.getenv("OUTPUT_CSV", "Analítica_Datos_Daniel_Carol.csv"),
        "COMMENT_COLUMN": os.getenv("COMMENT_COLUMN", "Comentario"),
        "ID_COLUMN": os.getenv("ID_COLUMN", "#"),
        "APOYO_CAROL_COLUMN": "Apoyo Carol",
        "SLEEP_MS": int(os.getenv("SLEEP_BETWEEN_BATCHES_MS", "200")),
        "TIMEOUT": 180
    }

def extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Extrae un JSON array de manera robusta."""
    if not text:
        return []

    cleaned = text.strip()
    # a) json.loads directo
    if cleaned.startswith("[") and cleaned.endswith("]"):
        try:
            return json.loads(cleaned)
        except:
            pass

    # b) Substring entre '[' y ']'
    try:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
    except:
        pass

    # c) Regex no codicioso
    try:
        match = re.search(r"\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*\]", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass

    return []

def call_ollama(config: Dict[str, Any], messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    url = f"{config['OLLAMA_HOST']}/api/chat"
    payload = {
        "model": config["OLLAMA_MODEL"],
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": config["TEMPERATURE"],
            "top_p": config["TOP_P"]
        }
    }
    
    for i in range(3):
        try:
            response = requests.post(url, json=payload, timeout=config["TIMEOUT"])
            response.raise_for_status()
            content = response.json().get("message", {}).get("content", "")
            
            results = extract_json_array(content)
            if results: return results
            
            try:
                # Intento de objeto único convertido a lista
                item = json.loads(content)
                return [item] if isinstance(item, dict) else []
            except:
                pass
        except Exception as e:
            wait = 2 ** i
            logging.warning(f"Intento {i+1} falló: {e}. Reintentando en {wait}s...")
            time.sleep(wait)
    return []

def classify_batch(config: Dict[str, Any], batch: List[Dict[str, str]]) -> Dict[str, str]:
    system_msg = config["CLASSIFIER_CONTEXT"]
    
    user_msg = (
        "Analiza los siguientes comentarios y devuelve SOLO JSON válido, sin texto extra.\n"
        "Formato exacto:\n"
        "[{\"id\":\"<id>\",\"apoyo\":\"FAVORABLE|CONTRARIO|NEUTRAL\"}]\n\n"
        "Comentarios:\n"
    )
    
    for item in batch:
        user_msg += f"- ID: {item['id']}, Comentario: {item['text']}\n"
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
    
    raw_results = call_ollama(config, messages)
    
    classified_data = {}
    valid_labels = {"FAVORABLE", "CONTRARIO", "NEUTRAL"}
    for res in raw_results:
        # Normalizar ID a string y label a mayúsculas
        rid = str(res.get("id", "")).strip()
        label = str(res.get("apoyo", "NEUTRAL")).strip().upper()
        if rid:
            classified_data[rid] = label if label in valid_labels else "NEUTRAL"
            
    return classified_data

def main():
    config = load_config()
    if not config["CLASSIFIER_CONTEXT"]:
        logging.error("CLASSIFIER_CONTEXT_CAROL es obligatorio en el .env")
        return

    input_path = config["INPUT_CSV"]
    if not os.path.exists(input_path):
        logging.error(f"No existe el archivo: {input_path}")
        return

    # Leer todo el archivo a memoria para permitir sobrescritura segura
    rows = []
    fieldnames = []
    with open(input_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []
        if config["APOYO_CAROL_COLUMN"] not in fieldnames:
            fieldnames.append(config["APOYO_CAROL_COLUMN"])
            
        for idx, row in enumerate(reader):
            # Usar el ID_COLUMN o el índice si no existe
            rid = str(row.get(config["ID_COLUMN"], idx)).strip()
            row["__id_internal__"] = rid
            rows.append(row)

    total = len(rows)
    logging.info(f"Procesando {total} comentarios para Carol Aviaga...")
    
    batch_size = config["BATCH_SIZE"]
    
    for i in range(0, total, batch_size):
        current_batch = rows[i:i + batch_size]
        payload = [
            {"id": r["__id_internal__"], "text": r[config["COMMENT_COLUMN"]]} 
            for r in current_batch
        ]
        
        logging.info(f"Batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
        results = classify_batch(config, payload)
        logging.info(f"Clasificados: {len(results)}/{len(current_batch)}")
        
        for r in current_batch:
            label = results.get(r["__id_internal__"], "NEUTRAL")
            r[config["APOYO_CAROL_COLUMN"]] = label

    # Guardar resultados
    output_path = config["OUTPUT_CSV"]
    with open(output_path, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[fn for fn in fieldnames if fn != "__id_internal__"])
        writer.writeheader()
        for r in rows:
            # Eliminar la clave temporal antes de escribir
            data = {k: v for k, v in r.items() if k != "__id_internal__"}
            writer.writerow(data)

    logging.info(f"Proceso completado. Archivo guardado en: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    main()
