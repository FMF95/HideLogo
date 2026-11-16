import sys
import os
import shutil
import subprocess
import tempfile
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw
from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QColorDialog, QFileDialog, QFormLayout, QGroupBox,
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QLineEdit, QProgressBar, QPushButton, QSpinBox, QSplitter, QVBoxLayout,
    QWidget,
)

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
VECTOR_EXTENSIONS = {".emf", ".wmf", ".svg", ".eps", ".pdf"}
INKSCAPE_EXPORT_EXTENSIONS = {".emf", ".eps", ".pdf"}


def _ruta_recurso(nombre: str) -> Path:
    """Devuelve la ruta de un recurso en ejecución normal o empaquetada."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "graphics" / nombre


def editar_imagen_vectorial(
    ruta_entrada: str,
    ruta_inkscape: str | None,
    x: float,
    y: float,
    ancho: float,
    alto: float,
    color_borde: str = "#FF0000",
    grosor_borde: float = 2.0,
    color_relleno: str = "none",
    ruta_salida: str | None = None,
) -> str:
    """Añade un rectángulo vectorial y conserva el formato cuando es posible.

    ``x``, ``y``, ``ancho`` y ``alto`` se expresan en las unidades del
    ``viewBox`` del SVG. Los formatos distintos de SVG se convierten
    temporalmente antes de editarse y se vuelven a exportar con Inkscape.
    """
    entrada = Path(ruta_entrada)
    inkscape = Path(ruta_inkscape) if ruta_inkscape else None
    if not entrada.exists():
        raise FileNotFoundError(f"No existe la imagen de entrada: {entrada}")
    if ancho <= 0 or alto <= 0 or grosor_borde < 0:
        raise ValueError("ancho, alto y grosor_borde deben ser valores válidos.")

    extension_entrada = entrada.suffix.lower()
    extension_salida = (
        Path(ruta_salida).suffix.lower() if ruta_salida else extension_entrada
    )
    necesita_inkscape = (
        extension_entrada != ".svg" or extension_salida != ".svg"
    )
    if necesita_inkscape and (inkscape is None or not inkscape.is_file()):
        raise FileNotFoundError(
            "Se necesita una ruta válida al ejecutable de Inkscape para "
            f"procesar {entrada.suffix}."
        )
    if extension_salida not in {".svg", *INKSCAPE_EXPORT_EXTENSIONS}:
        warnings.warn(
            f"Inkscape no exporta directamente a {extension_salida}; se usará SVG."
        )
        extension_salida = ".svg"
    salida = Path(ruta_salida) if ruta_salida else entrada.with_name(
        f"{entrada.stem}_editada{extension_salida}"
    )
    if salida.suffix.lower() != extension_salida:
        salida = salida.with_suffix(extension_salida)

    temporales = []
    try:
        if extension_entrada == ".svg":
            svg_origen = entrada
        else:
            fd, nombre = tempfile.mkstemp(suffix=".svg")
            os.close(fd)
            svg_origen = Path(nombre)
            temporales.append(svg_origen)
            _ejecutar_inkscape(inkscape, entrada, svg_origen)

        fd, nombre = tempfile.mkstemp(suffix=".svg")
        os.close(fd)
        svg_modificado = Path(nombre)
        temporales.append(svg_modificado)
        _inyectar_rectangulo_svg(
            svg_origen, svg_modificado, x, y, ancho, alto,
            color_borde, grosor_borde, color_relleno,
        )
        salida.parent.mkdir(parents=True, exist_ok=True)
        if extension_salida == ".svg":
            shutil.copyfile(svg_modificado, salida)
        else:
            _ejecutar_inkscape(inkscape, svg_modificado, salida)
        return str(salida)
    finally:
        for temporal in temporales:
            try:
                temporal.unlink(missing_ok=True)
            except OSError as error:
                warnings.warn(f"No se pudo eliminar {temporal}: {error}")


def _ejecutar_inkscape(inkscape: Path, entrada: Path, salida: Path) -> None:
    try:
        subprocess.run(
            [str(inkscape), str(entrada), "--export-filename", str(salida)],
            check=True, capture_output=True, text=True,
        )
    except (FileNotFoundError, PermissionError, subprocess.CalledProcessError) as error:
        detalle = (
            getattr(error, "stderr", None)
            or getattr(error, "stdout", None)
            or ""
        ).strip()
        raise RuntimeError(
            f"Inkscape no pudo procesar {entrada}: {detalle or error}"
        ) from error


def _inyectar_rectangulo_svg(
    origen: Path,
    destino: Path,
    x: float,
    y: float,
    ancho: float,
    alto: float,
    color_borde: str,
    grosor_borde: float,
    color_relleno: str,
) -> None:
    try:
        arbol = ET.parse(origen)
    except ET.ParseError as error:
        raise ValueError(f"El archivo no contiene un SVG válido: {origen}") from error
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    raiz = arbol.getroot()
    if raiz.tag.startswith("{"):
        namespace = raiz.tag[1:].split("}", 1)[0]
        if namespace != SVG_NS:
            raise ValueError(f"El SVG usa un namespace no compatible: {namespace}")
    rectangulo = ET.Element(
        f"{{{SVG_NS}}}rect",
        {
            "x": str(x), "y": str(y), "width": str(ancho), "height": str(alto),
            "stroke": color_borde, "stroke-width": str(grosor_borde),
            "fill": color_relleno,
        },
    )
    raiz.append(rectangulo)
    arbol.write(destino, encoding="utf-8", xml_declaration=True)


def _obtener_viewbox(ruta: Path, ruta_inkscape: Path | None = None):
    temporal = None
    try:
        svg = ruta
        if ruta.suffix.lower() != ".svg":
            if ruta_inkscape is None:
                return None
            fd, nombre = tempfile.mkstemp(suffix=".svg")
            os.close(fd)
            temporal = Path(nombre)
            _ejecutar_inkscape(ruta_inkscape, ruta, temporal)
            svg = temporal
        raiz = ET.parse(svg).getroot()
        valores = raiz.get("viewBox", "").replace(",", " ").split()
        if len(valores) == 4:
            return tuple(map(float, valores))
    except (ET.ParseError, ValueError):
        return None
    finally:
        if temporal:
            temporal.unlink(missing_ok=True)
    return None


class ImagePreviewWidget(QWidget):
    """Rectángulo almacenado siempre en coordenadas de la imagen original."""

    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.img_rect_x, self.img_rect_y = 50, 50
        self.img_rect_w, self.img_rect_h = 250, 100
        self.rect_color = QColor("white")
        self.dragging = self.resizing = False
        self.last_mouse = QPoint()
        self.scale = 1.0
        self.image_x = self.image_y = self.image_w = self.image_h = 0
        self.setMinimumHeight(500)

    def set_image(self, pixmap):
        self.pixmap = pixmap
        if pixmap:
            self.img_rect_x = self.img_rect_y = 50
            self.img_rect_w = min(250, max(20, pixmap.width() - 60))
            self.img_rect_h = min(100, max(20, pixmap.height() - 60))
        self.update()

    def set_rect_color(self, color):
        self.rect_color = color
        self.update()

    def get_rect(self):
        return tuple(map(int, (self.img_rect_x, self.img_rect_y,
                               self.img_rect_w, self.img_rect_h)))

    def image_to_screen(self):
        return QRect(
            int(self.image_x + self.img_rect_x * self.scale),
            int(self.image_y + self.img_rect_y * self.scale),
            int(self.img_rect_w * self.scale),
            int(self.img_rect_h * self.scale),
        )

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(220, 220, 220))
        if self.pixmap is None:
            return
        scaled = self.pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_x = (self.width() - scaled.width()) / 2
        self.image_y = (self.height() - scaled.height()) / 2
        self.image_w, self.image_h = scaled.width(), scaled.height()
        self.scale = scaled.width() / self.pixmap.width()
        painter.drawPixmap(int(self.image_x), int(self.image_y), scaled)
        rect = self.image_to_screen()
        painter.fillRect(rect, self.rect_color)
        painter.setPen(QPen(QColor(255, 0, 0), 1))
        painter.drawRect(rect)
        painter.fillRect(QRect(rect.right() - 7, rect.bottom() - 7, 9, 9),
                         QColor(255, 0, 0))

    def mousePressEvent(self, event):
        if self.pixmap is None:
            return
        rect = self.image_to_screen()
        handle = QRect(rect.right() - 10, rect.bottom() - 10, 20, 20)
        if handle.contains(event.pos()):
            self.resizing, self.last_mouse = True, event.pos()
        elif rect.contains(event.pos()):
            self.dragging, self.last_mouse = True, event.pos()

    def mouseMoveEvent(self, event):
        if self.pixmap is None:
            return
        dx = (event.pos().x() - self.last_mouse.x()) / self.scale
        dy = (event.pos().y() - self.last_mouse.y()) / self.scale
        if self.dragging:
            self.img_rect_x = max(0, min(self.img_rect_x + dx,
                                         self.pixmap.width() - self.img_rect_w))
            self.img_rect_y = max(0, min(self.img_rect_y + dy,
                                         self.pixmap.height() - self.img_rect_h))
        elif self.resizing:
            self.img_rect_w = max(20, self.img_rect_w + dx)
            self.img_rect_h = max(20, self.img_rect_h + dy)
            self.img_rect_w = min(self.img_rect_w,
                                  self.pixmap.width() - self.img_rect_x)
            self.img_rect_h = min(self.img_rect_h,
                                  self.pixmap.height() - self.img_rect_y)
        else:
            return
        self.last_mouse = event.pos()
        self.update()

    def mouseReleaseEvent(self, _event):
        self.dragging = self.resizing = False


class ImageEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.image_files, self.output_folder = [], ""
        self.inkscape_path = shutil.which("inkscape") or ""
        self.rect_color = QColor("white")
        self.logo_process = QIcon(str(_ruta_recurso("logo_cajero_1.ico")))
        self.logo_done = QIcon(str(_ruta_recurso("logo_cajero_2.ico")))
        self.logo_app = QIcon(str(_ruta_recurso("logo_cajero_3.ico")))
        self.setWindowIcon(self.logo_app)
        self.setWindowTitle("Editor de Imágenes")
        self.resize(1400, 850)
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left, left_layout = QWidget(), QVBoxLayout()
        left.setLayout(left_layout)
        self.btn_load = QPushButton("Seleccionar imágenes")
        self.btn_load.clicked.connect(self.select_images)
        self.list_images = QListWidget()
        self.list_images.currentRowChanged.connect(self.update_preview)
        left_layout.addWidget(self.btn_load)
        left_layout.addWidget(self.list_images)
        splitter.addWidget(left)

        right, right_layout = QWidget(), QVBoxLayout()
        right.setLayout(right_layout)
        settings_group, form = QGroupBox("Configuración"), QFormLayout()
        self.spin_width, self.spin_height = QSpinBox(), QSpinBox()
        self.spin_width.setRange(20, 10000)
        self.spin_width.setValue(250)
        self.spin_height.setRange(20, 10000)
        self.spin_height.setValue(100)
        self.btn_color = QPushButton("Color")
        self.btn_color.clicked.connect(self.choose_color)
        form.addRow("Ancho inicial:", self.spin_width)
        form.addRow("Alto inicial:", self.spin_height)
        form.addRow("Elegir color:", self.btn_color)
        settings_group.setLayout(form)
        right_layout.addWidget(settings_group)

        output_layout = QHBoxLayout()
        self.txt_output = QLineEdit()
        self.btn_output = QPushButton("Carpeta salida")
        self.btn_output.clicked.connect(self.select_output_folder)
        self.txt_output.setPlaceholderText("Carpeta de salida")
        output_layout.addWidget(self.txt_output)
        output_layout.addWidget(self.btn_output)
        right_layout.addLayout(output_layout)
        inkscape_layout = QHBoxLayout()
        self.txt_inkscape = QLineEdit(self.inkscape_path)
        self.txt_inkscape.setPlaceholderText("Ruta a inkscape.exe")
        btn_inkscape = QPushButton("Inkscape")
        btn_inkscape.clicked.connect(self.select_inkscape)
        inkscape_layout.addWidget(self.txt_inkscape)
        inkscape_layout.addWidget(btn_inkscape)
        right_layout.addLayout(inkscape_layout)
        self.preview = ImagePreviewWidget()
        right_layout.addWidget(self.preview)
        process_layout = QHBoxLayout()
        logo_frame = QFrame()
        logo_frame.setObjectName("processLogoFrame")
        logo_frame.setFrameShape(QFrame.Shape.StyledPanel)
        logo_frame.setStyleSheet(
            "#processLogoFrame { border: 1px solid #aaa; border-radius: 6px; "
            "background: #f5f5f5; }"
        )
        logo_frame.setMinimumSize(140, 140)
        logo_frame.setMaximumWidth(180)
        logo_layout = QVBoxLayout(logo_frame)
        self.logo_display = QLabel()
        self.logo_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(self.logo_display)
        process_layout.addWidget(logo_frame)

        process_controls = QVBoxLayout()
        self.progress = QProgressBar()
        process_controls.addWidget(self.progress)
        self.btn_process = QPushButton("Procesar imágenes")
        self.btn_process.clicked.connect(self.process_images)
        process_controls.addWidget(self.btn_process)
        self.btn_reset = QPushButton("Vaciar lista y restablecer")
        self.btn_reset.clicked.connect(self.reset)
        process_controls.addWidget(self.btn_reset)
        process_layout.addLayout(process_controls, 1)
        right_layout.addLayout(process_layout)
        self._set_process_logo(self.logo_process)
        splitter.addWidget(right)
        splitter.setSizes([350, 1000])
        root.addWidget(splitter)

    def _set_process_logo(self, logo):
        self.logo_display.setPixmap(logo.pixmap(QSize(112, 112)))

    def select_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar imágenes", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp "
            "*.emf *.wmf *.svg *.eps *.pdf)",
        )
        if not files:
            return
        self.image_files = files
        self.list_images.clear()
        for file in files:
            self.list_images.addItem(QListWidgetItem(Path(file).name))
        self.list_images.setCurrentRow(0)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            self.output_folder = folder
            self.txt_output.setText(folder)

    def select_inkscape(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar ejecutable de Inkscape", "",
            "Ejecutable de Inkscape (inkscape.exe);;Todos los archivos (*)",
        )
        if ruta:
            self.txt_inkscape.setText(ruta)

    def reset(self):
        self.image_files.clear()
        self.list_images.clear()
        self.preview.set_image(None)
        self.output_folder = ""
        self.txt_output.clear()
        self.txt_inkscape.setText(self.inkscape_path)
        self.spin_width.setValue(250)
        self.spin_height.setValue(100)
        self.rect_color = QColor("white")
        self.preview.set_rect_color(self.rect_color)
        self.btn_color.setStyleSheet("")
        self.progress.setValue(0)
        self._set_process_logo(self.logo_process)

    def choose_color(self):
        color = QColorDialog.getColor(self.rect_color, self)
        if color.isValid():
            self.rect_color = color
            self.preview.set_rect_color(color)
            self.btn_color.setStyleSheet(f"background:{color.name()};")

    def update_preview(self, row):
        if 0 <= row < len(self.image_files):
            self.preview.img_rect_w = self.spin_width.value()
            self.preview.img_rect_h = self.spin_height.value()
            self.preview.set_image(QPixmap(self.image_files[row]))

    def process_images(self):
        if not self.image_files:
            QMessageBox.warning(self, "Error", "Seleccione imágenes.")
            return
        self.output_folder = self.txt_output.text().strip()
        if not self.output_folder:
            QMessageBox.warning(self, "Error", "Seleccione carpeta de salida.")
            return
        output_folder = Path(self.output_folder)
        if not output_folder.is_dir():
            QMessageBox.warning(
                self, "Carpeta no válida",
                "La carpeta de salida no existe o no es una carpeta.",
            )
            return
        missing = [path for path in self.image_files if not Path(path).is_file()]
        if missing:
            QMessageBox.warning(
                self, "Archivos no encontrados",
                f"No se puede continuar: no existe {Path(missing[0]).name}.",
            )
            return
        try:
            fd, prueba_escritura = tempfile.mkstemp(
                prefix=".hide_logo_", dir=output_folder
            )
            os.close(fd)
            Path(prueba_escritura).unlink()
        except OSError as error:
            QMessageBox.warning(
                self, "Carpeta no escribible",
                f"No se puede escribir en la carpeta de salida:\n{error}",
            )
            return
        x, y, w, h = self.preview.get_rect()
        fill_color = (self.rect_color.red(), self.rect_color.green(),
                      self.rect_color.blue())
        ruta_inkscape_text = self.txt_inkscape.text().strip()
        ruta_inkscape = Path(ruta_inkscape_text) if ruta_inkscape_text else None
        vector_files = [
            Path(path) for path in self.image_files
            if Path(path).suffix.lower() in VECTOR_EXTENSIONS
        ]
        needs_inkscape = any(path.suffix.lower() != ".svg" for path in vector_files)
        if needs_inkscape and (ruta_inkscape is None or not ruta_inkscape.is_file()):
            QMessageBox.warning(
                self, "Inkscape no disponible",
                "Para editar formatos vectoriales distintos de SVG debe "
                "seleccionar un ejecutable válido de Inkscape.",
            )
            return
        output_paths = []
        for path in self.image_files:
            entrada = Path(path)
            extension = entrada.suffix
            if entrada.suffix.lower() == ".wmf":
                extension = ".svg"
            output_paths.append(output_folder / f"{entrada.stem}{extension}")
        existentes = [path for path in output_paths if path.exists()]
        if existentes:
            respuesta = QMessageBox.question(
                self, "Sobrescribir archivos",
                "Ya existen archivos de salida. ¿Desea sobrescribirlos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        total = len(self.image_files)
        self.progress.setValue(0)
        self._set_process_logo(self.logo_process)
        for idx, image_path in enumerate(self.image_files):
            entrada = Path(image_path)
            salida = output_paths[idx]
            if entrada.suffix.lower() in VECTOR_EXTENSIONS:
                try:
                    viewbox = _obtener_viewbox(entrada, ruta_inkscape)
                    if viewbox and self.preview.pixmap:
                        vx, vy, vw, vh = viewbox
                        x_v = vx + x * vw / self.preview.pixmap.width()
                        y_v = vy + y * vh / self.preview.pixmap.height()
                        w_v = w * vw / self.preview.pixmap.width()
                        h_v = h * vh / self.preview.pixmap.height()
                    else:
                        x_v, y_v, w_v, h_v = x, y, w, h
                    salida = Path(editar_imagen_vectorial(
                        str(entrada),
                        str(ruta_inkscape) if ruta_inkscape else None,
                        x_v, y_v, w_v, h_v,
                        color_borde="none", grosor_borde=0,
                        color_relleno=self.rect_color.name(), ruta_salida=str(salida),
                    ))
                except (FileNotFoundError, RuntimeError, ValueError, OSError) as error:
                    QMessageBox.critical(
                        self, "Error vectorial",
                        f"No se pudo procesar {entrada.name}:\n{error}",
                    )
                    return
            else:
                try:
                    img = Image.open(entrada).convert("RGB")
                    ImageDraw.Draw(img).rectangle(
                        [x, y, x + w, y + h], fill=fill_color
                    )
                    img.save(salida)
                except (OSError, ValueError) as error:
                    QMessageBox.critical(
                        self, "Error de imagen",
                        f"No se pudo procesar {entrada.name}:\n{error}",
                    )
                    return
            self.progress.setValue(int((idx + 1) * 100 / total))
        QMessageBox.information(self, "Finalizado",
                                 "Imágenes generadas correctamente.")
        self._set_process_logo(self.logo_done)


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(_ruta_recurso("logo_cajero_3.ico"))))
    window = ImageEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
