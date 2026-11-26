import json

with open('index.html', encoding='utf-8') as f:
    html = f.read()
with open('Datos/data_procesado.json', encoding='utf-8') as f:
    data = f.read()

tag = '<script id="inline-data">window.__INLINE_DATA__ = ' + data + ';</script>'
out = html.replace('</head>', tag + '\n</head>', 1)

dest = r'C:\Users\Ceres Tolvas\Downloads\dashboard_siembra_datos.html'
with open(dest, 'w', encoding='utf-8') as f:
    f.write(out)
print('OK:', round(len(out)/1024/1024, 1), 'MB')
