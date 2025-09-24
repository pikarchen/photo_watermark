import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QLabel, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
import os

class MainWindow(QMainWindow):
    # 字体选择
    from PyQt5.QtWidgets import QFontComboBox, QSpinBox, QColorDialog
    font_layout = QHBoxLayout()
    font_layout.addWidget(QLabel('字体:'))
    self.font_combo = QFontComboBox()
    font_layout.addWidget(self.font_combo)
    font_layout.addWidget(QLabel('字号:'))
    self.font_size_spin = QSpinBox()
    self.font_size_spin.setRange(10, 100)
    self.font_size_spin.setValue(32)
    font_layout.addWidget(self.font_size_spin)
    right_layout.addLayout(font_layout)

    # 颜色选择
    color_layout = QHBoxLayout()
    color_layout.addWidget(QLabel('颜色:'))
    self.color_btn = QPushButton('选择颜色')
    self.color_btn.clicked.connect(self.choose_color)
    self.watermark_color = (255, 0, 0)
    color_layout.addWidget(self.color_btn)
    right_layout.addLayout(color_layout)

    # 阴影效果
    self.shadow_checkbox = QPushButton('添加阴影效果')
    self.shadow_checkbox.setCheckable(True)
    right_layout.addWidget(self.shadow_checkbox)
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.watermark_color = (color.red(), color.green(), color.blue())
            self.color_btn.setStyleSheet(f'background-color: {color.name()};')
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Photo Watermark')
        self.resize(1200, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        main_layout = QHBoxLayout(self.central_widget)

        # 左侧：图片列表和导入按钮
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        btn_layout = QHBoxLayout()
        self.btn_import_single = QPushButton('导入单张图片')
        self.btn_import_multi = QPushButton('批量导入图片')
        self.btn_import_folder = QPushButton('导入文件夹')
        btn_layout.addWidget(self.btn_import_single)
        btn_layout.addWidget(self.btn_import_multi)
        btn_layout.addWidget(self.btn_import_folder)
        left_layout.addLayout(btn_layout)

        self.list_widget = QListWidget()
        left_layout.addWidget(QLabel('已导入图片列表：'))
        left_layout.addWidget(self.list_widget)

        # 导出按钮
        self.btn_export = QPushButton('导出图片')
        left_layout.addWidget(self.btn_export)

        main_layout.addWidget(left_widget, 2)

    # 右侧：图片预览区和水印设置
    right_widget = QWidget()
    right_layout = QVBoxLayout(right_widget)
    right_layout.addWidget(QLabel('图片预览：'))
    self.preview_label = QLabel()
    self.preview_label.setFixedSize(600, 600)
    self.preview_label.setAlignment(Qt.AlignCenter)
    right_layout.addWidget(self.preview_label)

    # 文本水印设置区
    right_layout.addWidget(QLabel('文本水印设置：'))
    self.watermark_text_input = QLabel('内容:')
    self.watermark_text = QPushButton('点击输入水印文本')
    self.watermark_text.setStyleSheet('text-align:left')
    self.watermark_text_val = ''
    self.watermark_text.clicked.connect(self.input_watermark_text)
    right_layout.addWidget(self.watermark_text_input)
    right_layout.addWidget(self.watermark_text)

    # 字体选择
    from PyQt5.QtWidgets import QFontComboBox, QSpinBox, QColorDialog, QSlider
    font_layout = QHBoxLayout()
    font_layout.addWidget(QLabel('字体:'))
    self.font_combo = QFontComboBox()
    font_layout.addWidget(self.font_combo)
    font_layout.addWidget(QLabel('字号:'))
    self.font_size_spin = QSpinBox()
    self.font_size_spin.setRange(10, 100)
    self.font_size_spin.setValue(32)
    font_layout.addWidget(self.font_size_spin)
    right_layout.addLayout(font_layout)

    # 颜色选择
    color_layout = QHBoxLayout()
    color_layout.addWidget(QLabel('颜色:'))
    self.color_btn = QPushButton('选择颜色')
    self.color_btn.clicked.connect(self.choose_color)
    self.watermark_color = (255, 0, 0)
    color_layout.addWidget(self.color_btn)
    right_layout.addLayout(color_layout)

    # 阴影效果
    self.shadow_checkbox = QPushButton('添加阴影效果')
    self.shadow_checkbox.setCheckable(True)
    right_layout.addWidget(self.shadow_checkbox)

    # 透明度调节
    self.opacity_label = QLabel('透明度: 100%')
    self.opacity_slider = QSlider(Qt.Horizontal)
    self.opacity_slider.setMinimum(10)
    self.opacity_slider.setMaximum(100)
    self.opacity_slider.setValue(100)
    self.opacity_slider.valueChanged.connect(self.update_opacity_label)
    right_layout.addWidget(self.opacity_label)
    right_layout.addWidget(self.opacity_slider)

    main_layout.addWidget(right_widget, 3)
    def input_watermark_text(self):
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, '输入水印文本', '水印内容：', text=self.watermark_text_val)
        if ok:
            self.watermark_text_val = text
            self.watermark_text.setText(text if text else '点击输入水印文本')

    def update_opacity_label(self, value):
        self.opacity_label.setText(f'透明度: {value}%')

        # 绑定事件
        self.btn_import_single.clicked.connect(self.import_single_image)
        self.btn_import_multi.clicked.connect(self.import_multi_images)
        self.btn_import_folder.clicked.connect(self.import_folder)
        self.list_widget.currentRowChanged.connect(self.show_preview)
        self.btn_export.clicked.connect(self.export_images)

        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_paths = []
        self.preview_label.clear()

    def import_single_image(self):
        file, _ = QFileDialog.getOpenFileName(self, '选择图片', '',
            '图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)')
        if file:
            self.add_image(file)

    def import_multi_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, '批量选择图片', '',
            '图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)')
        for file in files:
            self.add_image(file)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if folder:
            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext in self.supported_formats:
                    self.add_image(fpath)

    def add_image(self, path):
        if path not in self.image_paths:
            self.image_paths.append(path)
            item = QListWidgetItem(os.path.basename(path))
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                icon = QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(icon)
            self.list_widget.addItem(item)
            if len(self.image_paths) == 1:
                self.list_widget.setCurrentRow(0)

    def show_preview(self, row):
        if 0 <= row < len(self.image_paths):
            pixmap = QPixmap(self.image_paths[row])
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
            else:
                self.preview_label.clear()
        else:
            self.preview_label.clear()

    def export_images(self):
        if not self.image_paths:
            return
        folder = QFileDialog.getExistingDirectory(self, '选择导出文件夹')
        if not folder:
            return
        from PyQt5.QtWidgets import QInputDialog
        fmt, ok = QInputDialog.getItem(self, '选择导出格式', '格式：', ['JPEG', 'PNG'], 0, False)
        if not ok:
            return
        text = self.watermark_text_val
        opacity = self.opacity_slider.value() / 100.0
        font_family = self.font_combo.currentFont().family()
        font_size = self.font_size_spin.value()
        color_tuple = self.watermark_color
        shadow = self.shadow_checkbox.isChecked()
        for path in self.image_paths:
            fname = os.path.basename(path)
            name, ext = os.path.splitext(fname)
            out_ext = '.jpg' if fmt == 'JPEG' else '.png'
            out_path = os.path.join(folder, name + out_ext)
            if os.path.abspath(out_path) == os.path.abspath(path):
                out_path = os.path.join(folder, name + '_watermarked' + out_ext)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                if text:
                    from PyQt5.QtGui import QPainter, QColor, QFont
                    p = QPixmap(pixmap)
                    painter = QPainter(p)
                    painter.setRenderHint(QPainter.Antialiasing)
                    font = QFont(font_family, font_size)
                    painter.setFont(font)
                    color = QColor(*color_tuple)
                    color.setAlphaF(opacity)
                    painter.setPen(color)
                    rect = p.rect()
                    # 阴影效果
                    if shadow:
                        shadow_color = QColor(0, 0, 0)
                        shadow_color.setAlphaF(opacity * 0.5)
                        painter.setPen(shadow_color)
                        painter.drawText(rect.translated(2, 2), Qt.AlignCenter, text)
                        painter.setPen(color)
                    painter.drawText(rect, Qt.AlignCenter, text)
                    painter.end()
                    p.save(out_path, fmt)
                else:
                    pixmap.save(out_path, fmt)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
