import pandas as pd
import matplotlib.pyplot as plt

def generate_summary():
    # Load the CSV
    df = pd.read_csv('Analítica_Datos_Daniel_Carol.csv')
    
    # Columns to analyze
    figures = {
        "Daniel Ximénez": "Apoyo Daniel",
        "Carol Aviaga": "Apoyo Carol"
    }
    
    # Sentiments to count
    sentiments = ["FAVORABLE", "CONTRARIO", "NEUTRAL"]
    
    results = []
    
    for display_name, col_name in figures.items():
        # Count values for the current figure
        counts = df[col_name].value_counts()
        total = len(df[col_name].dropna())
        
        row = {"Figura": display_name}
        
        for sentiment in sentiments:
            count = counts.get(sentiment, 0)
            percentage = (count / total * 100) if total > 0 else 0
            row[sentiment] = f"{count} ({percentage:.1f}%)".replace('.', ',')
        
        row["Total"] = total
        results.append(row)
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(results)
    
    # Rename columns to match the image
    summary_df = summary_df[["Figura", "FAVORABLE", "CONTRARIO", "NEUTRAL", "Total"]]
    
    # Print the table
    print("\n2. Resultados cuantitativos\n")
    print(summary_df.to_string(index=False))

    # Save as Image
    fig, ax = plt.subplots(figsize=(10, 2))
    ax.axis('off')
    
    # Create the table
    table = ax.table(
        cellText=summary_df.values,
        colLabels=summary_df.columns,
        cellLoc='center',
        loc='center'
    )
    
    # Styling
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)
    
    # Header styling (bold)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#f2f2f2')
    
    plt.title("2. Resultados cuantitativos", loc='left', fontsize=16, fontweight='bold', pad=20)
    
    output_image = 'resultados_cuantitativos.png'
    plt.savefig(output_image, bbox_inches='tight', dpi=300)
    print(f"\nImagen guardada como: {output_image}")
    
    return summary_df

if __name__ == "__main__":
    generate_summary()
