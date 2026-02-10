"""
Script: plot_topics_distribution.py
Descripción: Genera una gráfica de torta con la distribución de la columna `Topic`
             a partir de un CSV (por defecto `Topics_Clean.csv`).

Uso:
    python plot_topics_distribution.py --input Topics_Clean.csv --output topics_distribution.png

Este script detecta la columna de comentarios o la columna `Topic` de forma heurística,
calcula conteos y porcentajes, dibuja la gráfica y guarda la imagen.
"""

import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def detect_topic_column(df: pd.DataFrame) -> str:
    """Detecta la columna que contiene el tópico (preferencias explícitas)."""
    candidates = ["Topic", "Topics", "topic", "topics", "Tópico", "Topico", "Topic Principal", "topic_principal"]
    for c in candidates:
        if c in df.columns:
            return c
    # Fallback: buscar columna con pocas categorías y valores cortos
    obj_cols = df.select_dtypes(include=['object']).columns
    if len(obj_cols) > 0:
        # elegir la columna con menor número de valores únicos (más probable que sea un topic)
        return min(obj_cols, key=lambda c: df[c].nunique())
    raise ValueError("No se pudo detectar la columna de tópicos en el CSV.")


def plot_distribution(counts: pd.Series, title: str, output_path: str, other_threshold: float = 0.0):
    """Dibuja y guarda un gráfico de dona con diseño mejorado."""
    total = counts.sum()
    labels = counts.index.astype(str).tolist()
    sizes = counts.values

    # Agrupar categorías pequeñas si se solicita
    if other_threshold > 0:
        pct = sizes / total
        mask = pct < other_threshold
        if mask.any() and mask.sum() < len(sizes):
            other_sum = sizes[mask].sum()
            labels = [lab for lab, m in zip(labels, ~mask) if m]
            sizes = [s for s, m in zip(sizes, ~mask) if m]
            labels.append('Otros')
            sizes.append(other_sum)

    # Diseño "Hermoso": Paleta de colores de alto contraste
    # Usamos colores saturados y muy distintos entre sí
    colors = [
        '#003f5c', # Azul Oscuro
        '#ffa600', # Naranja Dorado
        '#bc5090', # Magenta
        '#488f31', # Verde Bosque
        '#de425b', # Rojo Coral
        '#2f4b7c', # Azul Grisáceo
        '#665191', # Violeta
        '#a05195', # Púrpura
        '#d45087', # Rosa Fuerte
        '#f95d6a', # Salmón
    ]
    colors = colors[:len(labels)]
    
    fig, ax = plt.subplots(figsize=(12, 8), subplot_kw=dict(aspect="equal"))

    # Crear el gráfico de dona
    wedges, texts, autotexts = ax.pie(
        sizes, 
        autopct='%1.1f%%',
        startangle=140, 
        colors=colors,
        pctdistance=0.75, 
        explode=[0.03]*len(labels), # Separación sutil
        wedgeprops={'width': 0.5, 'edgecolor': 'white', 'linewidth': 1.5},
        textprops={'color': "black", 'weight': 'bold', 'fontsize': 12}
    )

    # Añadir leyenda a un lado con los totales incluidos
    legend_labels = [f"{l} (n={s})" for l, s in zip(labels, sizes)]
    ax.legend(
        wedges, legend_labels,
        title="Distribución de Tópicos",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=11,
        frameon=True,
        shadow=True
    )

    # Estilo de los porcentajes
    plt.setp(autotexts, size=11, weight="bold")

    # Título central
    plt.title(title, fontsize=20, fontweight='bold', pad=30, color='#222222')

    # Guardar con alta calidad
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logging.info(f"Gráfica rediseñada guardada en: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Genera la distribución de tópicos desde un CSV')
    parser.add_argument('--input', default='Topics_Clean.csv', help='CSV de entrada que contiene la columna Topic')
    parser.add_argument('--output', default='topics_distribution_v2.png', help='Ruta de la imagen de salida')
    parser.add_argument('--title', default='Análisis de Tópicos - Reporte Final', help='Título del gráfico')
    parser.add_argument('--other_threshold', type=float, default=0.0, help='Umbral (0-1) para agrupar categorías pequeñas')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        logging.error(f"Archivo de entrada no encontrado: {args.input}")
        return

    # Detección automática de delimitador
    with open(args.input, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        sep = ';' if ';' in first_line else ','
    
    df = pd.read_csv(args.input, encoding='utf-8-sig', sep=sep)

    try:
        topic_col = detect_topic_column(df)
    except ValueError as e:
        logging.error(str(e))
        return

    logging.info(f"Procesando tópicos desde '{topic_col}'...")

    counts = df[topic_col].fillna('No identificado').astype(str).value_counts()

    # Crear gráfico de torta (sin guardar CSV externo)
    plot_distribution(counts, args.title, args.output, other_threshold=args.other_threshold)


if __name__ == '__main__':
    main()
