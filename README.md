# HideLogo

Aplicación de escritorio para añadir un rectángulo de color sobre imágenes.
El rectángulo se puede mover y redimensionar en la previsualización antes de
procesar los archivos.

## Características

- Procesamiento por lotes de imágenes rasterizadas: PNG, JPG, JPEG, BMP, TIFF
  y WEBP.
- Edición vectorial de SVG, EMF, WMF, EPS y PDF mediante Inkscape.
- Conservación del formato vectorial cuando Inkscape permite exportarlo.
- Conversión automática a SVG para formatos vectoriales que no se puedan
  exportar directamente.
- Uso del `viewBox` del SVG para colocar correctamente el rectángulo.
- El borde rojo solo aparece en la previsualización; no se guarda en la
  imagen resultante.
- Confirmación única antes de sobrescribir archivos existentes.
- Barra de progreso y mensajes de error antes de iniciar operaciones inválidas.

## Requisitos

- Python 3.10 o posterior.
- PyQt6.
- Pillow.
- Inkscape, solo necesario para formatos vectoriales distintos de SVG o para
  exportar a un formato diferente de SVG.

Instalación de dependencias:

```powershell
python -m pip install PyQt6 Pillow
```

## Ejecución

```powershell
python ImageEditor.py
```

En la aplicación:

1. Selecciona una o varias imágenes.
2. Selecciona la carpeta de salida.
3. Si vas a procesar un formato que necesita Inkscape, indica la ruta de
   `inkscape.exe`.
4. Elige el color del relleno y ajusta la posición y el tamaño del rectángulo.
5. Pulsa **Procesar imágenes**.

Los archivos de salida conservan el nombre original. Si ya existe alguno, la
aplicación pregunta una sola vez si se deben sobrescribir. Los archivos WMF,
que no se exportan directamente en todas las instalaciones de Inkscape, se
generan como SVG.

## Función vectorial

El módulo incluye la función:

```python
editar_imagen_vectorial(
    ruta_entrada,
    ruta_inkscape,
    x,
    y,
    ancho,
    alto,
    color_borde="#FF0000",
    grosor_borde=2.0,
    color_relleno="none",
    ruta_salida=None,
)
```

Las coordenadas se expresan en las unidades del `viewBox` del SVG. La función
convierte temporalmente los formatos que no sean SVG, inserta un elemento
`rect` al final del documento y elimina los archivos temporales al terminar.
Para un SVG guardado como SVG no es necesario disponer de Inkscape.
