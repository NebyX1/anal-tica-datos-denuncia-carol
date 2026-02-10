import csv
import os

input_file = 'Topics_Clean.csv'
output_file = 'Topics_Clean_Tmp.csv'

# Primero, leemos los datos CON DELIMITADOR COMA
# (Ya que vimos que ahora tiene comas pero quizás el visor está confundido)
try:
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        # Forzar lectura con coma
        reader = list(csv.DictReader(f, delimiter=','))
        fieldnames = csv.DictReader(open(input_file, 'r', encoding='utf-8-sig')).fieldnames

    # Escribimos con PUNTO Y COMA para que Excel/Visores en español lo abran correctamente
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for row in reader:
            writer.writerow(row)

    os.replace(output_file, input_file)
    print(f"Archivo {input_file} convertido exitosamente a formato con PUNTO Y COMA (;).")
except Exception as e:
    print(f"Error: {e}")
