"""
ACTUALIZAR DATOS — Dashboard Siembra · John Deere Ceres Tolvas
==============================================================
Lee los archivos .geojson de la carpeta 'Datos', genera el JSON
procesado y abre el dashboard en el browser.

Archivos esperados en Datos\:
  siembra2026.geojson   → temporada actual (se reemplaza cada semana)
  siembra2025.geojson   → año pasado semanal (se reemplaza cada semana)
  siembra2025F.geojson  → año pasado final/completo

Uso: doble click en actualizar_datos.py
"""

import json, os, glob, threading, time, webbrowser, http.server, socketserver

# ── MAPEO DE TEMPORADAS POR NOMBRE DE ARCHIVO ────────────────────────────────
SEASON_MAP = {
    'siembra2026.geojson':  '2026',
    'siembra2025F.geojson': '2025F',
    'siembra2025f.geojson': '2025F',
    'siembra2025.geojson':  '2025',
    'data.geojson':         '2026',
    'data2025f.geojson':    '2025F',
    'datos2025.geojson':    '2025',
}

def detectar_temporada(nombre_archivo):
    label = SEASON_MAP.get(nombre_archivo)
    if label:
        return label
    n = nombre_archivo.lower()
    if '2026' in n:               return '2026'
    if '2025f' in n or 'final' in n: return '2025F'
    if '2025' in n:               return '2025'
    if '2024' in n:               return '2024'
    return nombre_archivo.replace('.geojson', '')

# ── MAPEO DE CULTIVOS ────────────────────────────────────────────────────────
def clasificar_cultivo(nombre):
    if not nombre: return 'OTROS'
    n = nombre.lower()
    if 'wheat' in n:    return 'Trigo'
    if 'barley' in n:   return 'Cebada'
    if 'oats' in n:     return 'Avena'
    if 'soybeans' in n: return 'Soja'
    if 'corn' in n:     return 'Maiz'
    if 'sunflower' in n: return 'Girasol'
    if 'canola' in n:   return 'Canola'
    return 'OTROS'

# ── FILTROS DE CALIDAD ───────────────────────────────────────────────────────
MIN_AREA_HA = 0.5

# ── PATHS ────────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(BASE, 'Datos')
os.chdir(BASE)

print("=" * 60)
print("  Dashboard Siembra — John Deere Ceres Tolvas")
print("=" * 60)

# ── PROCESAR GEOJSON ─────────────────────────────────────────────────────────
archivos = sorted(glob.glob(os.path.join(CARPETA, '*.geojson')))

if not archivos:
    print(f"\n  [ERROR] No se encontraron archivos .geojson en:\n  {CARPETA}")
    print("\n  Copiá los archivos descargados de Operations Center")
    print("  a la carpeta 'Datos' con estos nombres:")
    print("    siembra2026.geojson")
    print("    siembra2025.geojson")
    print("    siembra2025F.geojson")
    input("\nPresioná Enter para cerrar...")
    exit()

print(f"\n  Procesando {len(archivos)} archivo(s)...\n")

todos = []
filtrados = 0

for archivo in archivos:
    nombre = os.path.basename(archivo)
    size_kb = os.path.getsize(archivo) / 1024
    season_label = detectar_temporada(nombre)

    try:
        with open(archivo, encoding='utf-8') as f:
            gj = json.load(f)

        features = gj.get('features', [])
        procesados = 0
        descartados = 0

        for feat in features:
            p = feat.get('properties', {})

            partido  = (p.get('PARTIDO') or p.get('partido') or 'DESCONOCIDO').upper().strip()
            org      = (p.get('Organization Name') or '—').strip()
            crop_raw = (p.get('Crop Name') or '').strip()
            variety  = (p.get('Variety Name') or '—').strip()
            field_op = (p.get('Field Operation ID') or '').strip()

            # Temporada: si el archivo tiene nombre reconocible (siembra2026.geojson etc.)
            # se usa el label del nombre. Si no (ej: data.geojson), se extrae el año
            # de Start Date / End Date — más confiable que el campo Crop Season.
            if season_label in ('2026', '2025', '2025F'):
                season = season_label
            else:
                raw_date = p.get('Start Date') or p.get('End Date') or ''
                season = raw_date[:4] if len(raw_date) >= 4 else season_label

            var_area = float(p.get('Variety Area (ha)') or p.get('Area (ha)') or 0) or 0
            area     = float(p.get('Area (ha)') or 0) or 0
            tot_mat  = float(p.get('Variety Total Material') or p.get('Total Material') or 0) or 0
            vin      = (p.get('Machine VIN')   or 'N/A').strip()
            model    = (p.get('Machine Model') or 'N/A').strip()

            use_area = var_area if var_area > 0 else area
            if use_area < MIN_AREA_HA:
                descartados += 1
                continue

            todos.append({
                'partido':  partido,
                'org':      org,
                'season':   season,
                'crop':     clasificar_cultivo(crop_raw),
                'crop_raw': crop_raw,
                'variety':      variety,
                'fieldOpId':    field_op,
                'area':         round(use_area, 2),
                'totalMaterial':round(tot_mat, 1),
                'vin':          vin,
                'model':        model,
            })
            procesados += 1

        filtrados += descartados
        print(f"  v {nombre} [{season_label}] ({size_kb:.0f} KB) — {procesados} registros ({descartados} desc.)")

    except Exception as e:
        print(f"  x Error en {nombre}: {e}")

output = os.path.join(CARPETA, 'data_procesado.json')
with open(output, 'w', encoding='utf-8') as f:
    json.dump(todos, f, ensure_ascii=False, separators=(',', ':'))

size_final = os.path.getsize(output) / 1024
temporadas = sorted(set(r['season'] for r in todos))
print(f"\n  v data_procesado.json: {len(todos)} registros · {size_final:.0f} KB")
print(f"    Temporadas: {', '.join(temporadas)}")
if filtrados:
    print(f"    Descartados: {filtrados} outliers / área mínima")

# ── ABRIR DASHBOARD ───────────────────────────────────────────────────────────
PORT = 3001
URL  = f"http://localhost:{PORT}/index.html"

print(f"\n  Abriendo dashboard en {URL}")
print("  Cerrá esta ventana para detener el servidor.\n")
print("=" * 60)

class SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

def abrir_browser():
    time.sleep(0.8)
    webbrowser.open(URL)

threading.Thread(target=abrir_browser, daemon=True).start()

try:
    with socketserver.TCPServer(("", PORT), SilentHandler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\n  Servidor detenido.")
except OSError as e:
    if e.errno in (98, 10048):  # address already in use (Linux/Windows)
        print(f"  Puerto {PORT} ocupado — abriendo browser igual...")
        webbrowser.open(URL)
        input("\nPresioná Enter para cerrar...")
    else:
        raise
