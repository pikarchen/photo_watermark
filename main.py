import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QLabel, QHBoxLayout,
    QFontComboBox, QSpinBox, QColorDialog, QSlider, QInputDialog
)
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QTransform
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    TEMPLATE_FILE = 'watermark_templates.json'
    LAST_TEMPLATE_FILE = 'last_watermark.json'
    def get_current_params(self):
        return {
            'watermark_text': self.watermark_text_val,
            'font_family': self.font_combo.currentFont().family(),
            'font_size': self.font_size_spin.value(),
            'watermark_color': self.watermark_color,
            'shadow': self.shadow_checkbox.isChecked(),
            'opacity': self.opacity_slider.value(),
            'watermark_pos': self.watermark_pos,
            'rotate_angle': self.rotate_slider.value(),
            'imgwm_path': self.imgwm_path,
            'imgwm_scale': self.imgwm_scale_slider.value(),
            'imgwm_opacity': self.imgwm_opacity_slider.value()
        }

    def set_params(self, params):
        self.watermark_text_val = params.get('watermark_text', '')
        self.watermark_text.setText(self.watermark_text_val or '点击输入水印文本')
        font_family = params.get('font_family', self.font_combo.currentFont().family())
        self.font_combo.setCurrentFont(QFont(font_family))
        self.font_size_spin.setValue(params.get('font_size', 32))
        self.watermark_color = tuple(params.get('watermark_color', (255, 0, 0)))
        self.shadow_checkbox.setChecked(params.get('shadow', False))
        self.opacity_slider.setValue(params.get('opacity', 100))
        self.set_watermark_position(params.get('watermark_pos', 4))
        self.rotate_slider.setValue(params.get('rotate_angle', 0))
        self.imgwm_path = params.get('imgwm_path', None)
        if self.imgwm_path:
            pixmap = QPixmap(self.imgwm_path)
            if not pixmap.isNull():
                self.imgwm_preview.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.imgwm_scale_slider.setValue(params.get('imgwm_scale', 100))
        self.imgwm_opacity_slider.setValue(params.get('imgwm_opacity', 100))

    def save_template(self):
        name, ok = QInputDialog.getText(self, '保存模板', '模板名称：')
        if not ok or not name:
            return
        params = self.get_current_params()
        templates = self.load_templates_file()
        templates[name] = params
        self.save_templates_file(templates)
        self.load_templates()

    def load_template(self, item=None):
        if item is None:
            item = self.template_list.currentItem()
        if not item:
            return
        name = item.text()
        templates = self.load_templates_file()
        params = templates.get(name)
        if params:
            self.set_params(params)
            self.save_last_template(params)

    def delete_template(self):
        item = self.template_list.currentItem()
        if not item:
            return
        name = item.text()
        templates = self.load_templates_file()
        if name in templates:
            del templates[name]
            self.save_templates_file(templates)
            self.load_templates()

    def load_templates(self):
        self.template_list.clear()
        templates = self.load_templates_file()
        for name in templates:
            self.template_list.addItem(name)

    def load_templates_file(self):
        if os.path.exists(self.TEMPLATE_FILE):
            try:
                with open(self.TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_templates_file(self, templates):
        with open(self.TEMPLATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

    def save_last_template(self, params=None):
        if params is None:
            params = self.get_current_params()
        with open(self.LAST_TEMPLATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=2)

    def load_last_template(self):
        if os.path.exists(self.LAST_TEMPLATE_FILE):
            try:
                with open(self.LAST_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                    params = json.load(f)
                    self.set_params(params)
            except Exception:
                pass
        elif self.template_list.count() > 0:
            # 默认加载第一个模板
            item = self.template_list.item(0)
            self.load_template(item)
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Photo Watermark')
        self.resize(1200, 700)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QHBoxLayout(self.central_widget)

        # 左侧布局
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
        self.btn_export = QPushButton('导出图片')
        left_layout.addWidget(self.btn_export)
        main_layout.addWidget(left_widget, 2)

        # 右侧布局
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
        self.opacity_slider = QSlider()
        self.opacity_slider.setOrientation(Qt.Horizontal)
        self.opacity_slider.setMinimum(10)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        right_layout.addWidget(self.opacity_label)
        right_layout.addWidget(self.opacity_slider)

        # 水印位置九宫格
        right_layout.addWidget(QLabel('水印位置：'))
        pos_layout = QHBoxLayout()
        self.pos_buttons = []
        pos_names = ['左上', '上中', '右上', '左中', '中心', '右中', '左下', '下中', '右下']
        for i, name in enumerate(pos_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self.set_watermark_position(idx))
            self.pos_buttons.append(btn)
            pos_layout.addWidget(btn)
        self.watermark_pos = 4  # 默认中心
        self.pos_buttons[self.watermark_pos].setChecked(True)
        right_layout.addLayout(pos_layout)

        # 水印旋转
        self.rotate_label = QLabel('水印旋转: 0°')
        self.rotate_slider = QSlider()
        self.rotate_slider.setOrientation(Qt.Horizontal)
        self.rotate_slider.setMinimum(-180)
        self.rotate_slider.setMaximum(180)
        self.rotate_slider.setValue(0)
        self.rotate_slider.valueChanged.connect(self.update_rotate_label)
        right_layout.addWidget(self.rotate_label)
        right_layout.addWidget(self.rotate_slider)

        # 图片水印设置区
        right_layout.addWidget(QLabel('图片水印设置：'))
        imgwm_layout = QHBoxLayout()
        self.imgwm_btn = QPushButton('选择水印图片')
        self.imgwm_btn.clicked.connect(self.choose_img_watermark)
        self.imgwm_path = None
        imgwm_layout.addWidget(self.imgwm_btn)
        self.imgwm_preview = QLabel()
        self.imgwm_preview.setFixedSize(64, 64)
        imgwm_layout.addWidget(self.imgwm_preview)
        right_layout.addLayout(imgwm_layout)

        # 图片水印缩放
        self.imgwm_scale_label = QLabel('缩放: 100%')
        self.imgwm_scale_slider = QSlider()
        self.imgwm_scale_slider.setOrientation(Qt.Horizontal)
        self.imgwm_scale_slider.setMinimum(10)
        self.imgwm_scale_slider.setMaximum(200)
        self.imgwm_scale_slider.setValue(100)
        self.imgwm_scale_slider.valueChanged.connect(self.update_imgwm_scale_label)
        right_layout.addWidget(self.imgwm_scale_label)
        right_layout.addWidget(self.imgwm_scale_slider)

        # 图片水印透明度
        self.imgwm_opacity_label = QLabel('水印透明度: 100%')
        self.imgwm_opacity_slider = QSlider()
        self.imgwm_opacity_slider.setOrientation(Qt.Horizontal)
        self.imgwm_opacity_slider.setMinimum(10)
        self.imgwm_opacity_slider.setMaximum(100)
        self.imgwm_opacity_slider.setValue(100)
        self.imgwm_opacity_slider.valueChanged.connect(self.update_imgwm_opacity_label)
        right_layout.addWidget(self.imgwm_opacity_label)
        right_layout.addWidget(self.imgwm_opacity_slider)

        # 模板管理按钮区
        template_btn_layout = QHBoxLayout()
        self.btn_save_template = QPushButton('保存模板')
        self.btn_load_template = QPushButton('加载模板')
        self.btn_delete_template = QPushButton('删除模板')
        template_btn_layout.addWidget(self.btn_save_template)
        template_btn_layout.addWidget(self.btn_load_template)
        template_btn_layout.addWidget(self.btn_delete_template)
        right_layout.addLayout(template_btn_layout)

        # 模板选择列表
        self.template_list = QListWidget()
        right_layout.addWidget(QLabel('模板列表：'))
        right_layout.addWidget(self.template_list)

        main_layout.addWidget(right_widget, 3)

        # 事件绑定
        self.btn_save_template.clicked.connect(self.save_template)
        self.btn_load_template.clicked.connect(self.load_template)
        self.btn_delete_template.clicked.connect(self.delete_template)
        self.template_list.itemDoubleClicked.connect(self.load_template)

        self.load_templates()
        self.load_last_template()

        # 事件绑定和数据初始化
        self.btn_import_single.clicked.connect(self.import_single_image)
        self.btn_import_multi.clicked.connect(self.import_multi_images)
        self.btn_import_folder.clicked.connect(self.import_folder)
        self.list_widget.currentRowChanged.connect(self.show_preview)
        self.btn_export.clicked.connect(self.export_images)
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.image_paths = []
        self.preview_label.clear()

    def input_watermark_text(self):
        text, ok = QInputDialog.getText(self, '输入水印文本', '水印内容：', text=self.watermark_text_val)
        if ok:
            self.watermark_text_val = text
            self.watermark_text.setText(text if text else '点击输入水印文本')

    def update_opacity_label(self, value):
        self.opacity_label.setText(f'透明度: {value}%')

    def update_imgwm_scale_label(self, value):
        self.imgwm_scale_label.setText(f'缩放: {value}%')

    def update_imgwm_opacity_label(self, value):
        self.imgwm_opacity_label.setText(f'水印透明度: {value}%')

    def update_rotate_label(self, value):
        self.rotate_label.setText(f'水印旋转: {value}°')

    def set_watermark_position(self, idx):
        self.watermark_pos = idx
        for i, btn in enumerate(self.pos_buttons):
            btn.setChecked(i == idx)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.watermark_color = (color.red(), color.green(), color.blue())

    def choose_img_watermark(self):
        file, _ = QFileDialog.getOpenFileName(self, '选择水印图片', '', '图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)')
        if file:
            self.imgwm_path = file
            pixmap = QPixmap(file)
            if not pixmap.isNull():
                self.imgwm_preview.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def import_single_image(self):
        file, _ = QFileDialog.getOpenFileName(self, '选择图片', '', '图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)')
        if file:
            self.add_image(file)

    def import_multi_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, '批量选择图片', '', '图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff)')
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
        fmt, ok = QInputDialog.getItem(self, '选择导出格式', '格式：', ['JPEG', 'PNG'], 0, False)
        if not ok:
            return
        text = self.watermark_text_val
        opacity = self.opacity_slider.value() / 100.0
        font_family = self.font_combo.currentFont().family()
        font_size = self.font_size_spin.value()
        color_tuple = self.watermark_color
        shadow = self.shadow_checkbox.isChecked()
        imgwm_path = self.imgwm_path
        imgwm_scale = self.imgwm_scale_slider.value() / 100.0
        imgwm_opacity = self.imgwm_opacity_slider.value() / 100.0
        rotate_angle = self.rotate_slider.value()
        pos_idx = self.watermark_pos
        pos_map = [
            (0, 0), (0.5, 0), (1, 0),
            (0, 0.5), (0.5, 0.5), (1, 0.5),
            (0, 1), (0.5, 1), (1, 1)
        ]
        for path in self.image_paths:
            fname = os.path.basename(path)
            name, ext = os.path.splitext(fname)
            out_ext = '.jpg' if fmt == 'JPEG' else '.png'
            out_path = os.path.join(folder, name + out_ext)
            if os.path.abspath(out_path) == os.path.abspath(path):
                out_path = os.path.join(folder, name + '_watermarked' + out_ext)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                p = QPixmap(pixmap)
                painter = QPainter(p)
                painter.setRenderHint(QPainter.Antialiasing)
                # 文本水印
                if text:
                    font = QFont(font_family, font_size)
                    painter.setFont(font)
                    color = QColor(*color_tuple)
                    color.setAlphaF(opacity)
                    painter.setPen(color)
                    rect = p.rect()
                    # 位置
                    x_ratio, y_ratio = pos_map[pos_idx]
                    x = int(rect.width() * x_ratio)
                    y = int(rect.height() * y_ratio)
                    align = Qt.AlignLeft if x_ratio == 0 else (Qt.AlignRight if x_ratio == 1 else Qt.AlignHCenter)
                    valign = Qt.AlignTop if y_ratio == 0 else (Qt.AlignBottom if y_ratio == 1 else Qt.AlignVCenter)
                    align_flag = align | valign
                    # 旋转
                    if rotate_angle != 0:
                        painter.save()
                        center = rect.center()
                        painter.translate(center)
                        painter.rotate(rotate_angle)
                        painter.translate(-center)
                    if shadow:
                        shadow_color = QColor(0, 0, 0)
                        shadow_color.setAlphaF(opacity * 0.5)
                        painter.setPen(shadow_color)
                        painter.drawText(rect.translated(2, 2), align_flag, text)
                        painter.setPen(color)
                    painter.drawText(rect, align_flag, text)
                    if rotate_angle != 0:
                        painter.restore()
                # 图片水印
                if imgwm_path:
                    wm_pixmap = QPixmap(imgwm_path)
                    if not wm_pixmap.isNull():
                        # 缩放
                        wm_w = int(wm_pixmap.width() * imgwm_scale)
                        wm_h = int(wm_pixmap.height() * imgwm_scale)
                        wm_pixmap = wm_pixmap.scaled(wm_w, wm_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        # 旋转
                        if rotate_angle != 0:
                            transform = QTransform().rotate(rotate_angle)
                            wm_pixmap = wm_pixmap.transformed(transform, Qt.SmoothTransformation)
                        # 透明度处理
                        temp_pixmap = QPixmap(wm_pixmap.size())
                        temp_pixmap.fill(Qt.transparent)
                        temp_painter = QPainter(temp_pixmap)
                        temp_painter.setOpacity(imgwm_opacity)
                        temp_painter.drawPixmap(0, 0, wm_pixmap)
                        temp_painter.end()
                        # 位置
                        x_ratio, y_ratio = pos_map[pos_idx]
                        x = int((p.width() - wm_pixmap.width()) * x_ratio)
                        y = int((p.height() - wm_pixmap.height()) * y_ratio)
                        painter.drawPixmap(x, y, temp_pixmap)
                painter.end()
                p.save(out_path, fmt)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
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
        imgwm_path = self.imgwm_path
        imgwm_scale = self.imgwm_scale_slider.value() / 100.0
        imgwm_opacity = self.imgwm_opacity_slider.value() / 100.0
        rotate_angle = self.rotate_slider.value()
        pos_idx = self.watermark_pos
        pos_map = [
            (0, 0), (0.5, 0), (1, 0),
            (0, 0.5), (0.5, 0.5), (1, 0.5),
            (0, 1), (0.5, 1), (1, 1)
        ]
        for path in self.image_paths:
            fname = os.path.basename(path)
            name, ext = os.path.splitext(fname)
            out_ext = '.jpg' if fmt == 'JPEG' else '.png'
            out_path = os.path.join(folder, name + out_ext)
            if os.path.abspath(out_path) == os.path.abspath(path):
                out_path = os.path.join(folder, name + '_watermarked' + out_ext)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                from PyQt5.QtGui import QPainter, QColor, QFont, QTransform
                p = QPixmap(pixmap)
                painter = QPainter(p)
                painter.setRenderHint(QPainter.Antialiasing)
                # 文本水印
                if text:
                    font = QFont(font_family, font_size)
                    painter.setFont(font)
                    color = QColor(*color_tuple)
                    color.setAlphaF(opacity)
                    painter.setPen(color)
                    rect = p.rect()
                    # 位置
                    x_ratio, y_ratio = pos_map[pos_idx]
                    x = int(rect.width() * x_ratio)
                    y = int(rect.height() * y_ratio)
                    align = Qt.AlignLeft if x_ratio == 0 else (Qt.AlignRight if x_ratio == 1 else Qt.AlignHCenter)
                    valign = Qt.AlignTop if y_ratio == 0 else (Qt.AlignBottom if y_ratio == 1 else Qt.AlignVCenter)
                    align_flag = align | valign
                    # 旋转
                    if rotate_angle != 0:
                        painter.save()
                        center = rect.center()
                        painter.translate(center)
                        painter.rotate(rotate_angle)
                        painter.translate(-center)
                    if shadow:
                        shadow_color = QColor(0, 0, 0)
                        shadow_color.setAlphaF(opacity * 0.5)
                        painter.setPen(shadow_color)
                        painter.drawText(rect.translated(2, 2), align_flag, text)
                        painter.setPen(color)
                    painter.drawText(rect, align_flag, text)
                    if rotate_angle != 0:
                        painter.restore()
                # 图片水印
                if imgwm_path:
                    wm_pixmap = QPixmap(imgwm_path)
                    if not wm_pixmap.isNull():
                        # 缩放
                        wm_w = int(wm_pixmap.width() * imgwm_scale)
                        wm_h = int(wm_pixmap.height() * imgwm_scale)
                        wm_pixmap = wm_pixmap.scaled(wm_w, wm_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        # 旋转
                        if rotate_angle != 0:
                            transform = QTransform().rotate(rotate_angle)
                            wm_pixmap = wm_pixmap.transformed(transform, Qt.SmoothTransformation)
                        # 透明度处理
                        temp_pixmap = QPixmap(wm_pixmap.size())
                        temp_pixmap.fill(Qt.transparent)
                        temp_painter = QPainter(temp_pixmap)
                        temp_painter.setOpacity(imgwm_opacity)
                        temp_painter.drawPixmap(0, 0, wm_pixmap)
                        temp_painter.end()
                        # 位置
                        x_ratio, y_ratio = pos_map[pos_idx]
                        x = int((p.width() - wm_pixmap.width()) * x_ratio)
                        y = int((p.height() - wm_pixmap.height()) * y_ratio)
                        painter.drawPixmap(x, y, temp_pixmap)
                painter.end()
                p.save(out_path, fmt)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
