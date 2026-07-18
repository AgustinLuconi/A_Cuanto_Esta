"""
Descarga logos oficiales de los 9 supermercados.

Intenta URLs en orden de prioridad (Wikimedia Commons primero,
luego CDN oficial). Usa Pillow para resize y cairosvg para
convertir SVG a PNG si es necesario.

Uso:
    cd backend && source venv/bin/activate
    python scripts/download_logos.py          # solo descarga los que faltan
    python scripts/download_logos.py --force  # reemplaza todos
"""
import io
import os
import sys
import warnings

import requests
import urllib3
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOGOS_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "static", "logos")
MAX_W, MAX_H = 400, 200
PLACEHOLDER_MAX_BYTES = 1_000  # placeholder < 1 KB

# Wikimedia requiere un User-Agent con descripción y contacto (T400119)
UA_WIKIMEDIA = "ACuantoEsta/1.0 (https://github.com/AgustinLuconi/A_Cuanto_Esta; agusluconi06@gmail.com)"
UA_BROWSER   = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

def _headers(url: str) -> dict:
    """Elige el User-Agent apropiado según el host."""
    if "wikimedia.org" in url or "wikipedia.org" in url:
        return {"User-Agent": UA_WIKIMEDIA}
    return {"User-Agent": UA_BROWSER}

# URLs verificadas. Prioridad: Wikimedia Commons (SVG directo) → CDN oficial.
# Las URLs de Wikimedia Commons usan el archivo SVG original (no CDN thumbnail),
# que se descarga directamente y se convierte con cairosvg.
LOGO_URLS: dict[str, list[str]] = {
    "coto": [
        # Wikimedia Commons — SVG directo, verificado OK
        "https://upload.wikimedia.org/wikipedia/commons/a/a5/Logo_Supermercado_Coto.svg",
    ],
    "carrefour": [
        # Wikipedia EN — SVG directo, verificado OK (logo del grupo Carrefour)
        "https://upload.wikimedia.org/wikipedia/en/6/65/Carrefour_Groupe.svg",
    ],
    "dia": [
        # Wikimedia Commons — SVG Dia 2019, verificado OK
        "https://upload.wikimedia.org/wikipedia/commons/c/c7/Dia_2019.svg",
    ],
    "disco": [
        # Wikimedia Commons — SVG Disco Supermercado, verificado OK
        "https://upload.wikimedia.org/wikipedia/commons/0/07/Disco-Supermarket-Logo.svg",
    ],
    "vea": [
        # Wikimedia Commons — PNG Vea Cencosud, verificado OK (29 KB)
        "https://upload.wikimedia.org/wikipedia/commons/f/fc/Logo_Vea_Cencosud.png",
    ],
    "la_anonima": [
        # Wikimedia Commons — JPEG, verificado OK (67 KB)
        "https://upload.wikimedia.org/wikipedia/commons/4/4d/Supermercados_La_anonima_logo.jpg",
    ],
    "jumbo": [
        # VTEX Jumbo AR — og:image del sitio oficial, verificado OK (600x601 RGBA)
        "https://jumboargentinaio.vtexassets.com/assets/vtex.file-manager-graphql/images/f6057f1f-8694-4a53-8310-2be46ca00397___81e6efd7f5e25248d2438427af2cfa63.png",
    ],
    "chango_mas": [
        # VTEX Chango Más (Mas Online) — SVG del theme, verificado OK (400x76 RGBA)
        "https://masonlineprod.vtexassets.com/assets/vtex.file-manager-graphql/images/1f676005-1a66-4379-abe1-e8c39b539f10___3b7e04ce085fbfa38121c0692ad1dd9b.svg",
    ],
    "atomo": [
        # El dominio correcto es atomoconviene.com (sin .ar)
        "https://atomoconviene.com/atomo-ecommerce/img/atomo-online-logo-1611013266.jpg",
    ],
}


def is_placeholder(path: str) -> bool:
    """True si el archivo actual es un placeholder (< 1 KB)."""
    try:
        return os.path.getsize(path) <= PLACEHOLDER_MAX_BYTES
    except FileNotFoundError:
        return True


def fetch(url: str, session: requests.Session) -> tuple[bytes, str] | None:
    """Descarga URL. Retorna (bytes, content_type) o None si falla."""
    try:
        r = session.get(url, headers=_headers(url), timeout=15, verify=False)
        if r.status_code != 200:
            return None
        ct = r.headers.get("content-type", "").split(";")[0].strip().lower()
        # Rechazar respuestas HTML (error pages)
        if "html" in ct:
            return None
        return r.content, ct
    except Exception:
        return None


def to_png(data: bytes, content_type: str) -> Image.Image | None:
    """Convierte bytes a imagen Pillow. Soporta PNG, JPEG, WebP y SVG."""
    if "svg" in content_type:
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(bytestring=data, output_width=400)
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            return None
    try:
        return Image.open(io.BytesIO(data))
    except Exception:
        return None


def resize(img: Image.Image) -> Image.Image:
    """Redimensiona a máximo MAX_W × MAX_H manteniendo aspect ratio."""
    img.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
    return img


def save_as_png(img: Image.Image, path: str) -> None:
    """Guarda como PNG. Si no tiene canal alpha, convierte a RGBA."""
    if img.mode not in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    img.save(path, "PNG", optimize=True)


def download_logo(name: str, urls: list[str], session: requests.Session) -> bool:
    """
    Intenta descargar el logo de cada URL en orden.
    Retorna True si se descargó correctamente.
    """
    dest = os.path.join(LOGOS_DIR, f"{name}.png")
    for url in urls:
        result = fetch(url, session)
        if result is None:
            continue
        data, ct = result
        img = to_png(data, ct)
        if img is None:
            continue
        img = resize(img)
        save_as_png(img, dest)
        size_kb = os.path.getsize(dest) / 1024
        print(f"  OK     {name:<14} | {img.size[0]}×{img.size[1]}px | {size_kb:.1f} KB | {url[:70]}")
        return True
    return False


def run(force: bool = False) -> None:
    os.makedirs(LOGOS_DIR, exist_ok=True)
    session = requests.Session()

    ok_list:   list[str] = []
    fail_list: list[str] = []
    skip_list: list[str] = []

    print("=== Descarga de logos de supermercados ===\n")

    for name, urls in LOGO_URLS.items():
        dest = os.path.join(LOGOS_DIR, f"{name}.png")
        if not force and not is_placeholder(dest):
            size_kb = os.path.getsize(dest) / 1024
            print(f"  SKIP   {name:<14} | ya descargado ({size_kb:.1f} KB)")
            skip_list.append(name)
            continue

        if download_logo(name, urls, session):
            ok_list.append(name)
        else:
            print(f"  FAIL   {name:<14} | ninguna URL funcionó — placeholder conservado")
            fail_list.append(name)

    print(f"\n=== Resumen ===")
    print(f"Descargados  : {len(ok_list)}   {ok_list}")
    print(f"Ya existían  : {len(skip_list)}  {skip_list}")
    print(f"Fallaron     : {len(fail_list)}  {fail_list}")

    if fail_list:
        print("\nLogos que quedaron con placeholder:")
        for name in fail_list:
            print(f"  - app/static/logos/{name}.png")
        print("Reemplazarlos manualmente copiando un PNG real con ese nombre exacto.")

    session.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    run(force=force)
