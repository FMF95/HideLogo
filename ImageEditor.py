import sys
from pathlib import Path

from PIL import Image, ImageDraw
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QColorDialog, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)


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

    def paintEvent(self, event):
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
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawRect(rect)
        painter.fillRect(QRect(rect.right() - 10, rect.bottom() - 10, 12, 12),
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

    def mouseReleaseEvent(self, event):
        self.dragging = self.resizing = False


class ImageEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.image_files, self.output_folder = [], ""
        self.rect_color = QColor("white")
        self.setWindowTitle("Editor Masivo de Imágenes")
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
        self.btn_color = QPushButton("Elegir color")
        self.btn_color.clicked.connect(self.choose_color)
        form.addRow("Ancho inicial:", self.spin_width)
        form.addRow("Alto inicial:", self.spin_height)
        form.addRow("Color:", self.btn_color)
        settings_group.setLayout(form)
        right_layout.addWidget(settings_group)

        output_layout = QHBoxLayout()
        self.btn_output = QPushButton("Carpeta salida")
        self.btn_output.clicked.connect(self.select_output_folder)
        self.lbl_output = QLabel("No seleccionada")
        output_layout.addWidget(self.btn_output)
        output_layout.addWidget(self.lbl_output)
        right_layout.addLayout(output_layout)
        self.preview = ImagePreviewWidget()
        right_layout.addWidget(self.preview)
        self.progress = QProgressBar()
        right_layout.addWidget(self.progress)
        self.btn_process = QPushButton("Procesar imágenes")
        self.btn_process.clicked.connect(self.process_images)
        right_layout.addWidget(self.btn_process)
        splitter.addWidget(right)
        splitter.setSizes([350, 1000])
        root.addWidget(splitter)

    def select_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar imágenes", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)",
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
            self.lbl_output.setText(folder)

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
        if not self.output_folder:
            QMessageBox.warning(self, "Error", "Seleccione carpeta de salida.")
            return
        x, y, w, h = self.preview.get_rect()
        fill_color = (self.rect_color.red(), self.rect_color.green(),
                      self.rect_color.blue())
        total = len(self.image_files)
        self.progress.setValue(0)
        for idx, image_path in enumerate(self.image_files):
            img = Image.open(image_path).convert("RGB")
            ImageDraw.Draw(img).rectangle([x, y, x + w, y + h], fill=fill_color)
            img.save(Path(self.output_folder) / Path(image_path).name)
            self.progress.setValue(int((idx + 1) * 100 / total))
        QMessageBox.information(self, "Finalizado",
                                 "Imágenes generadas correctamente.")


def main():
    app = QApplication(sys.argv)
    window = ImageEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
