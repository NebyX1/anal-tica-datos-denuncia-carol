import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import os

def create_wordcloud(input_file, output_image):
    if not os.path.exists(input_file):
        print(f"Error: El archivo {input_file} no existe.")
        return

    # Cargar los datos
    print(f"Leyendo {input_file}...")
    df = pd.read_csv(input_file)
    
    # Combinar todos los comentarios en un solo texto
    text = " ".join(cat for cat in df.Comentario.astype(str))
    
    # Lista extendida de Stopwords en Español
    spanish_stopwords = {
        'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para', 'con', 
        'no', 'una', 'su', 'al', 'lo', 'como', 'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 
        'porque', 'esta', 'entre', 'cuando', 'muy', 'sin', 'sobre', 'también', 'me', 'hasta', 'hay', 
        'donde', 'quien', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra', 
        'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mí', 'antes', 'algunos', 'qué', 'unos', 
        'yo', 'otro', 'otras', 'otra', 'él', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 'nada', 
        'muchos', 'cual', 'poco', 'ella', 'estar', 'estas', 'algunas', 'algo', 'nosotros', 'mi', 
        'mis', 'tú', 'te', 'ti', 'tu', 'tus', 'si', 'ser', 'es', 'era', 're', 'tan', 'va', 've', 'son',
        'ha', 'han', 'hace', 'hacer', 'puede', 'pueden', 'ver', 'comentarios', 'facebook', 'post', 'https', 'comentario'
    }
    
    # Combinar con las stopwords de la librería
    all_stopwords = set(STOPWORDS).union(spanish_stopwords)

    print("Generando nube de palabras...")
    
    # Configuración de diseño "hermoso"
    wordcloud = WordCloud(
        width=1600, 
        height=800,
        background_color='white',
        colormap='viridis',      # Colores vibrantes (puedes probar 'plasma', 'magma', 'inferno')
        stopwords=all_stopwords,
        min_font_size=10,
        max_words=200,
        contour_width=3,
        contour_color='steelblue',
        collocations=False,       # Evita que se repitan palabras combinadas
        include_numbers=False,
        random_state=42
    ).generate(text)

    # Mostrar y guardar
    plt.figure(figsize=(20, 10), facecolor=None)
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.tight_layout(pad=0)
    
    # Guardar imagen
    plt.savefig(output_image, format="png", dpi=300)
    print(f"¡Éxito! Nube de palabras guardada como '{output_image}'")
    
    # Opcional: mostrar en pantalla si tienes interfaz gráfica
    # plt.show()

if __name__ == "__main__":
    input_csv = "comentarios_fb_limpios.csv"
    output_png = "nube_comentarios.png"
    create_wordcloud(input_csv, output_png)
