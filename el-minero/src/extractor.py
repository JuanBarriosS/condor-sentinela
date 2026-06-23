"""
El Minero - Story #2
Extrae el texto plano de cada PDF descargado (data/raw_pdfs) usando pdfplumber,
y guarda el resultado como un archivo JSON por PDF en data/extracted_text.

Cada JSON generado tiene esta forma:
{
    "codigo": "001-26",
    "archivo_origen": "001-26.pdf",
    "num_paginas": 12,
    "texto_por_pagina": ["...", "...", ...],
    "texto_completo": "..."
}
"""

import os
import json
import pdfplumber

RAW_PDFS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_pdfs")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "extracted_text")


def extraer_texto_de_pdf(ruta_pdf):
    """
    Abre un PDF con pdfplumber y extrae el texto de cada pagina.
    Devuelve una lista de strings (uno por pagina) y el texto completo unido.
    Si una pagina no tiene texto extraible (ej. esta escaneada como imagen),
    se guarda como string vacio en esa posicion, sin romper el resto.
    """
    texto_por_pagina = []

    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            texto_por_pagina.append(texto if texto else "")

    texto_completo = "\n\n".join(texto_por_pagina)
    return texto_por_pagina, texto_completo


def procesar_pdf(nombre_archivo):
    """
    Procesa un solo PDF: extrae su texto y guarda el resultado como JSON.
    Si el JSON de salida ya existe, se omite (igual que el scraper con los PDFs).
    """
    codigo = nombre_archivo.replace(".pdf", "")
    ruta_pdf = os.path.join(RAW_PDFS_DIR, nombre_archivo)
    ruta_json = os.path.join(OUTPUT_DIR, f"{codigo}.json")

    if os.path.exists(ruta_json):
        print(f"  [SKIP] Ya existe: {codigo}.json")
        return

    try:
        texto_por_pagina, texto_completo = extraer_texto_de_pdf(ruta_pdf)
    except Exception as e:
        print(f"  [ERROR] No se pudo procesar {nombre_archivo}: {e}")
        return

    resultado = {
        "codigo": codigo,
        "archivo_origen": nombre_archivo,
        "num_paginas": len(texto_por_pagina),
        "texto_por_pagina": texto_por_pagina,
        "texto_completo": texto_completo,
    }

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"  [OK] Extraido: {codigo}.json ({len(texto_por_pagina)} paginas)")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.isdir(RAW_PDFS_DIR):
        print(f"[ERROR] No existe la carpeta de PDFs: {RAW_PDFS_DIR}")
        print("Corre primero scraper.py (Story #1) para descargar los PDFs.")
        return

    archivos_pdf = sorted(
        f for f in os.listdir(RAW_PDFS_DIR) if f.lower().endswith(".pdf")
    )

    if not archivos_pdf:
        print(f"[AVISO] No hay archivos PDF en {RAW_PDFS_DIR}")
        return

    print(f"Encontrados {len(archivos_pdf)} archivos PDF para procesar.\n")

    total_ok = 0
    total_error = 0
    total_skip = 0

    for nombre_archivo in archivos_pdf:
        codigo = nombre_archivo.replace(".pdf", "")
        ruta_json = os.path.join(OUTPUT_DIR, f"{codigo}.json")

        ya_existia = os.path.exists(ruta_json)
        procesar_pdf(nombre_archivo)

        if ya_existia:
            total_skip += 1
        elif os.path.exists(ruta_json):
            total_ok += 1
        else:
            total_error += 1

    print(f"\nListo.")
    print(f"  Extraidos correctamente: {total_ok}")
    print(f"  Omitidos (ya existian):  {total_skip}")
    print(f"  Con error:               {total_error}")
    print(f"JSONs guardados en: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()