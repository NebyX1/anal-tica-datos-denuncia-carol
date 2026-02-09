import os
import pandas as pd
import matplotlib.pyplot as plt

"""
Genera dos gráficos de torta (Apoyo Daniel, Apoyo Carol) y los guarda en un solo PNG.
"""

def load_counts(df: pd.DataFrame, col: str):
    # Normalizar valores
    vals = df[col].astype(str).str.strip().str.upper()
    counts = vals.value_counts()
    return {
        'FAVORABLE': int(counts.get('FAVORABLE', 0)),
        'CONTRARIO': int(counts.get('CONTRARIO', 0)),
        'NEUTRAL': int(counts.get('NEUTRAL', 0))
    }


def make_pie(ax, counts, title, colors):
    labels = []
    sizes = []
    for k in ['FAVORABLE', 'CONTRARIO', 'NEUTRAL']:
        labels.append(f"{k} ({counts[k]})")
        sizes.append(counts[k])

    # Evitar dividir por cero
    total = sum(sizes)
    if total == 0:
        ax.text(0.5, 0.5, 'No data', horizontalalignment='center', verticalalignment='center', fontsize=12)
        ax.set_title(title)
        ax.axis('off')
        return

    explode = [0.05 if s == max(sizes) else 0 for s in sizes]

    wedges, texts, autotexts = ax.pie(
        sizes,
        explode=explode,
        labels=None,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 0 else '',
        startangle=140,
        colors=colors,
        wedgeprops=dict(width=0.45, edgecolor='white')
    )

    # Draw center circle for donut look
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    ax.add_artist(centre_circle)

    ax.set_title(title, fontsize=14, fontweight='bold')
    # Legend on bottom
    ax.legend(wedges, labels, title='Etiqueta', loc='lower center', bbox_to_anchor=(0.5, -0.12), ncol=3)
    ax.axis('equal')


if __name__ == '__main__':
    input_csv = 'Analítica_Datos_Daniel_Carol.csv'
    if not os.path.exists(input_csv):
        print(f"Archivo no encontrado: {input_csv}")
        raise SystemExit(1)

    df = pd.read_csv(input_csv, encoding='utf-8-sig')

    # Asegurar que existan las columnas esperadas
    for col in ['Apoyo Daniel', 'Apoyo Carol']:
        if col not in df.columns:
            print(f"Advertencia: columna '{col}' no encontrada en {input_csv}. Se rellenará con ceros.")
            df[col] = ''

    counts_daniel = load_counts(df, 'Apoyo Daniel')
    counts_carol = load_counts(df, 'Apoyo Carol')

    # Colores elegantes: Daniel (verde, rojo, gris), Carol (blue, orange, grey)
    colors_daniel = ['#2E8B57', '#D9534F', '#9E9E9E']
    colors_carol = ['#0072B2', '#FF7F0E', '#9E9E9E']

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    make_pie(axes[0], counts_daniel, 'Distribución - Apoyo Daniel', colors_daniel)
    make_pie(axes[1], counts_carol, 'Distribución - Apoyo Carol', colors_carol)

    plt.suptitle('Distribución de Etiquetas (FAVORABLE / CONTRARIO / NEUTRAL)', fontsize=16, y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    out_png = 'apoyo_pie_charts.png'
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    print(f"Guardado: {os.path.abspath(out_png)}")
