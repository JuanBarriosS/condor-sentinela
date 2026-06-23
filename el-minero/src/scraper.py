import os
import re
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://alertastempranas.defensoria.gov.co/"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_pdfs")
PAUSA_ENTRE_REQUESTS = 1.0  

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}


def detectar_total_paginas(html):
    match = re.search(r"P[aá]gina\s+\d+\s+de\s+(\d+)", html, re.IGNORECASE)
    if match:
        return int(match.group(1))
    print("  [AVISO] No se pudo detectar el total de paginas, se usara 1")
    return 1


def normalizar_url_pdf(href):
    return href.replace("\\", "/")


def extraer_alertas_de_pagina(html):
    """
    Recorre cada fila <tr> de la tabla principal y extrae:
      - codigo de la alerta (ej. 001-26)
      - tipo (Estructural / Inminencia)
      - url del PDF de la alerta
      - url del PDF del informe de seguimiento, si existe
    Devuelve una lista de diccionarios.
    """
    soup = BeautifulSoup(html, "html.parser")
    filas = soup.select("table tr")

    alertas = []
    for fila in filas:
        celdas = fila.find_all("td")
        if not celdas:
            continue  # es la fila de encabezado <th>, se ignora

        codigo = celdas[0].get_text(strip=True)
        tipo = celdas[1].get_text(strip=True) if len(celdas) > 1 else None

        # Buscar el link de PDF de la alerta (esta en la columna "PDF")
        link_pdf_alerta = None
        for a in fila.find_all("a", href=True):
            if "/alertas" in a["href"] or "/alertas\\" in a["href"]:
                if a["href"].lower().endswith(".pdf"):
                    link_pdf_alerta = normalizar_url_pdf(a["href"])
                    break

        # Buscar el link de PDF del informe de seguimiento, si existe
        link_pdf_informe = None
        for a in fila.find_all("a", href=True):
            if "/informes" in a["href"] or "/informes\\" in a["href"]:
                if a["href"].lower().endswith(".pdf"):
                    link_pdf_informe = normalizar_url_pdf(a["href"])
                    break

        if codigo and link_pdf_alerta:
            alertas.append({
                "codigo": codigo,
                "tipo": tipo,
                "pdf_alerta": link_pdf_alerta,
                "pdf_informe": link_pdf_informe,
            })

    return alertas


def descargar_pdf(url, destino):
    """Descarga un PDF y lo guarda en disco si no existe ya."""
    if os.path.exists(destino):
        print(f"  [SKIP] Ya existe: {os.path.basename(destino)}")
        return

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        with open(destino, "wb") as f:
            f.write(resp.content)
        print(f"  [OK] Descargado: {os.path.basename(destino)}")
    except requests.RequestException as e:
        print(f"  [ERROR] No se pudo descargar {url}: {e}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_alertas = 0

    # Primero se carga la pagina 1 para detectar cuantas paginas hay en total
    print("Cargando pagina 1 para detectar el total de paginas...")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] No se pudo cargar la pagina inicial: {e}")
        return

    total_paginas = detectar_total_paginas(resp.text)
    print(f"Total de paginas detectadas: {total_paginas}")

    # Se procesa la pagina 1 ya descargada, y luego el resto
    html_por_pagina = {1: resp.text}
    for pagina in range(2, total_paginas + 1):
        url_pagina = f"{BASE_URL}?page={pagina}"
        try:
            r = requests.get(url_pagina, headers=HEADERS, timeout=30)
            r.raise_for_status()
            html_por_pagina[pagina] = r.text
        except requests.RequestException as e:
            print(f"  [ERROR] No se pudo cargar la pagina {pagina}: {e}")
        time.sleep(PAUSA_ENTRE_REQUESTS)

    for pagina, html in html_por_pagina.items():
        print(f"\nProcesando pagina {pagina}/{total_paginas}")

        alertas = extraer_alertas_de_pagina(html)
        print(f"  Encontradas {len(alertas)} alertas en esta pagina")

        for alerta in alertas:
            codigo = alerta["codigo"]
            nombre_archivo = f"{codigo}.pdf"
            destino = os.path.join(OUTPUT_DIR, nombre_archivo)
            descargar_pdf(alerta["pdf_alerta"], destino)

            # Si tiene informe de seguimiento tambien se descarga con sufijo
            if alerta["pdf_informe"]:
                nombre_informe = f"{codigo}_informe.pdf"
                destino_informe = os.path.join(OUTPUT_DIR, nombre_informe)
                descargar_pdf(alerta["pdf_informe"], destino_informe)

            total_alertas += 1

    print(f"\nListo. Total de alertas procesadas: {total_alertas}")
    print(f"PDFs guardados en: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
