import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QLabel, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Photo Watermark')
        self.resize(900, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        # 导入图片按钮区
        btn_layout = QHBoxLayout()
        self.btn_import_single = QPushButton('导入单张图片')
        self.btn_import_multi = QPushButton('批量导入图片')
        self.btn_import_folder = QPushButton('导入文件夹')
        btn_layout.addWidget(self.btn_import_single)
        btn_layout.addWidget(self.btn_import_multi)
        btn_layout.addWidget(self.btn_import_folder)
        self.layout.addLayout(btn_layout)

        # 图片列表区
        self.list_widget = QListWidget()
        self.layout.addWidget(QLabel('已导入图片列表：'))
        self.layout.addWidget(self.list_widget)

        # 绑定事件
        self.btn_import_single.clicked.connect(self.import_single_image)
        self.btn_import_multi.clicked.connect(self.import_multi_images)
        self.btn_import_folder.clicked.connect(self.import_folder)

        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_paths = []

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
