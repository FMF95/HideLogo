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
- Panel de estado con un icono que cambia al finalizar correctamente.
- Botones independientes para restablecer el diseño o vaciar la lista.
- Icono de aplicación configurable mediante los archivos incluidos en
  `graphics/`.

## Requisitos

- Python 3.10 o posterior.
- PyQt6.
- Pillow.
- PyInstaller, solo para generar el ejecutable.
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

El botón **Restablecer diseño** recupera el tamaño y el color iniciales y
restablece el rectángulo de la previsualización, pero conserva las imágenes
cargadas, la carpeta de salida y la ruta de Inkscape.

El botón **Vaciar lista** elimina únicamente las imágenes cargadas y limpia la
previsualización. Ambos botones devuelven el logo de estado a
`logo_cajero_1.ico`; no ejecutan la acción del otro botón.

## Iconos

Los iconos deben permanecer en la carpeta `graphics/` junto a estos nombres:

- `logo_cajero_1.ico`: icono inicial del panel de procesamiento.
- `logo_cajero_2.ico`: icono mostrado tras completar correctamente el proceso.
- `logo_cajero_3.ico`: icono de la ventana y de la aplicación.

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

## Crear un ejecutable Windows

El proyecto incluye [HideLogo.spec](D:/Programación/HideLogo/HideLogo.spec).
Este archivo configura:

- Un único ejecutable (`onefile`).
- Aplicación gráfica sin ventana de terminal (`console=False`).
- `logo_cajero_3.ico` como icono del archivo `.exe`.
- Inclusión embebida de la carpeta `graphics/`; no es necesario distribuirla
  junto al ejecutable.

Desde PowerShell, situado en la carpeta del proyecto, ejecuta:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --clean --noconfirm HideLogo.spec
```

El ejecutable se generará en:

```text
dist\HideLogo.exe
```

Para distribuir la aplicación basta con copiar `dist\HideLogo.exe`. La carpeta
`graphics/` y el código fuente no son necesarios en el equipo de destino.
Inkscape sí debe estar instalado en el equipo si se van a editar formatos
vectoriales distintos de SVG; la ruta a `inkscape.exe` se selecciona desde la
aplicación.

Si se modifican los iconos o el código, vuelve a ejecutar el comando de
compilación. Las carpetas `build/` y `dist/` son artefactos generados por
PyInstaller y pueden eliminarse antes de una compilación limpia.