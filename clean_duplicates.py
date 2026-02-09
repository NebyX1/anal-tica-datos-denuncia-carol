import csv
import os
import re

def clean_text(text):
    if not text:
        return ""
    # Elimina espacios múltiples, tabulaciones y saltos de línea extra
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def clean_duplicates(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Error: El archivo {input_file} no existe.")
        return

    comentarios_vistos = set()
    filas_limpias = []
    total_filas = 0
    duplicados = 0

    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            total_filas += 1
            
            # Limpiamos el texto del comentario para la comparación y para el resultado
            comentario_original = row.get('Comentario', '')
            comentario_limpio = clean_text(comentario_original)
            
            # Normalizamos para la detección de duplicados (minúsculas)
            comentario_norm = comentario_limpio.lower()
            
            if comentario_norm and comentario_norm not in comentarios_vistos:
                comentarios_vistos.add(comentario_norm)
                # Actualizamos la fila con el texto limpio y el nuevo índice
                row['Comentario'] = comentario_limpio
                row['#'] = len(filas_limpias) + 1
                filas_limpias.append(row)
            else:
                duplicados += 1

    # Guardamos el archivo limpio
    with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filas_limpias)
    
    print(f"Limpieza completada:")
    print(f"- Filas procesadas: {total_filas}")
    print(f"- Comentarios duplicados o vacíos eliminados: {duplicados}")
    print(f"- Filas únicas resultantes: {len(filas_limpias)}")
    print(f"- Archivo guardado como: {output_file}")

if __name__ == "__main__":
    input_csv = "comentarios_fb.csv"
    output_csv = "comentarios_fb_limpios.csv"
    clean_duplicates(input_csv, output_csv)
