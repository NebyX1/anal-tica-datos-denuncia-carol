import pandas as pd
import os

def sortear_casos():
    input_file = 'Analítica_Datos_Daniel_Carol.csv'
    output_file = 'Casos_Sorteados.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: No se encontró el archivo {input_file}")
        return

    # Cargar los datos
    df = pd.read_csv(input_file)
    total_casos = len(df)
    
    print(f"Total de casos disponibles: {total_casos}")
    
    # Sortear 200 casos (o todos si hay menos de 200)
    n_sorteo = min(200, total_casos)
    df_sorteados = df.sample(n=n_sorteo, random_state=42) # random_state para reproducibilidad
    
    # Guardar los sorteados
    df_sorteados.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"¡Sorteo completado! Se han guardado {n_sorteo} casos en '{output_file}'.")

if __name__ == "__main__":
    sortear_casos()
