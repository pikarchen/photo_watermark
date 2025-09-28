#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
水印文件本地应用
支持文本和图片水印，批量处理图片文件
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                            QLineEdit, QTextEdit, QSlider, QSpinBox, QComboBox,
                            QFileDialog, QListWidget, QListWidgetItem, QTabWidget,
                            QGroupBox, QCheckBox, QColorDialog, QFontDialog,
                            QProgressBar, QMessageBox, QSplitter, QFrame,
                            QScrollArea, QSizePolicy, QSpacerItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtGui import (QPixmap, QPainter, QFont, QColor, QPen, QBrush,
                        QImage, QFontMetrics, QTransform, QIcon)
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import json
import math
import threading

# 在创建 QApplication 之前，自动设置 Qt 插件路径（兼容 PyQt5\Qt 与 PyQt5\Qt5 布局）
def _ensure_qt_plugin_env():
    try:
        import PyQt5
        import os
        import os.path as p
        base = p.dirname(PyQt5.__file__)
        for qt_folder in ("Qt", "Qt5"):
            plugins = p.join(base, qt_folder, "plugins")
            platforms = p.join(plugins, "platforms")
            bin_dir = p.join(base, qt_folder, "bin")
            if os.path.exists(platforms):
                # 仅当未手动设置时写入，避免覆盖用户已有环境
                os.environ.setdefault("QT_PLUGIN_PATH", plugins)
                os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", platforms)
                if os.path.exists(bin_dir):
                    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
                break
    except Exception:
        pass

# 供预览与导出共用的字体选择逻辑
def get_font_for_text(family: str, size: int, is_bold: bool = False, is_italic: bool = False, text: str = ""):
    """返回 (font, has_real_bold, has_real_italic)。优先中文字体和匹配样式。"""
    try:
        fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
        mapping = {
            'Microsoft YaHei': ('msyh.ttc', 'msyhbd.ttc', None, None),
            'SimSun': ('simsun.ttc', None, None, None),
            'SimHei': ('simhei.ttf', None, None, None),
            'Arial': ('arial.ttf', 'arialbd.ttf', 'ariali.ttf', 'arialbi.ttf'),
            'Times New Roman': ('times.ttf', 'timesbd.ttf', 'timesi.ttf', 'timesbi.ttf'),
        }

        def select_variant(fam: str):
            reg, bold, italic, bolditalic = mapping.get(fam, (None, None, None, None))
            if is_bold and is_italic and bolditalic:
                return bolditalic, True, True
            if is_bold and bold:
                return bold, True, False
            if is_italic and italic:
                return italic, False, True
            return reg, False, False

        def has_cjk(s: str) -> bool:
            for ch in s:
                code = ord(ch)
                if (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF) or (0x20000 <= code <= 0x2A6DF):
                    return True
            return False

        search_order = []
        if has_cjk(text):
            search_order.extend(['Microsoft YaHei', 'SimSun', 'SimHei'])
        if family not in search_order:
            search_order.insert(0, family)

        tried = set()
        for fam in search_order:
            fname, real_bold, real_italic = select_variant(fam)
            if not fname:
                continue
            fpath = os.path.join(fonts_dir, fname)
            if fpath in tried:
                continue
            tried.add(fpath)
            if os.path.exists(fpath):
                return ImageFont.truetype(fpath, size=size), real_bold, real_italic

        try:
            return ImageFont.truetype(family, size=size), False, False
        except Exception:
            return ImageFont.load_default(), False, False
    except Exception:
        return ImageFont.load_default(), False, False

class ExportThread(QThread):
    """导出线程"""
    progress_updated = pyqtSignal(int, int, str)  # current, total, filename
    finished = pyqtSignal(int, int, list)  # success_count, error_count, errors
    
    def __init__(self, image_list, output_folder, settings):
        super().__init__()
        self.image_list = image_list
        self.output_folder = output_folder
        self.settings = settings
        
    def run(self):
        success_count = 0
        error_count = 0
        errors = []
        
        for i, image_path in enumerate(self.image_list):
            try:
                # 发送进度更新
                self.progress_updated.emit(i + 1, len(self.image_list), os.path.basename(image_path))
                
                # 加载图片（用上下文确保句柄及时释放）
                with Image.open(image_path) as image:
                    image.load()
                    # 添加水印
                    watermarked_image = self.add_watermark_to_image(image)
                
                # 生成输出文件名
                output_filename = self.generate_output_filename(image_path)
                output_path = os.path.join(self.output_folder, output_filename)
                
                # 保存图片
                if self.settings['format'] == 'JPEG':
                    if watermarked_image.mode == 'RGBA':
                        rgb_image = Image.new('RGB', watermarked_image.size, (255, 255, 255))
                        rgb_image.paste(watermarked_image, mask=watermarked_image.split()[-1])
                        watermarked_image = rgb_image
                    with open(output_path, 'wb') as f:
                        watermarked_image.save(f, 'JPEG', quality=self.settings['quality'])
                else:  # PNG
                    with open(output_path, 'wb') as f:
                        watermarked_image.save(f, 'PNG')
                    
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"{os.path.basename(image_path)}: {str(e)}")
                
        # 发送完成信号
        self.finished.emit(success_count, error_count, errors)
        
    def add_watermark_to_image(self, image):
        """为图片添加水印（复制主类的逻辑）"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
            
        # 创建水印层
        watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)

        wm_type = self.settings.get('watermark_type', '文本水印')
        if wm_type == '图片水印':
            # 与预览一致的图片水印
            path = self.settings.get('image_watermark_path')
            if path and os.path.exists(path):
                try:
                    with Image.open(path) as wm_img:
                        if wm_img.mode != 'RGBA':
                            wm_img = wm_img.convert('RGBA')
                        op = max(0, min(100, int(self.settings.get('image_watermark_opacity', 70)))) / 100.0
                        if op < 1.0:
                            alpha = wm_img.split()[-1].point(lambda p: int(p * op))
                            wm_img.putalpha(alpha)
                        # 放置位置沿用文本位置计算（以水印图片尺寸为准）
                        pos = self._calc_pos_by_setting(image.size, wm_img.size)
                        watermark.paste(wm_img, pos, wm_img)
                except Exception:
                    pass
        else:
            # 文本水印参数
            wm = self.settings['watermark_settings']
            text = wm.get('text', '水印文字')
            font_size = wm.get('font_size', 24)
            opacity = wm.get('opacity', 70)
            font_family = wm.get('font_family', 'Microsoft YaHei')
            is_bold = wm.get('is_bold', False)
            is_italic = wm.get('is_italic', False)
            # 优先使用预览解析好的字体路径，确保导出与预览一致
            resolved = self.settings.get('resolved_font_path')
            if resolved and os.path.exists(resolved):
                try:
                    font = ImageFont.truetype(resolved, size=font_size)
                    # 粗体判定：若路径对应粗体文件名，视为真实粗体
                    name = os.path.basename(resolved).lower()
                    has_real_bold = ('bd' in name) or ('bold' in name)
                    has_real_italic = ('i.' in name) or ('italic' in name) or ('bi' in name)
                except Exception:
                    font, has_real_bold, has_real_italic = get_font_for_text(
                        font_family, font_size, is_bold=is_bold, is_italic=is_italic, text=text
                    )
            else:
                font, has_real_bold, has_real_italic = get_font_for_text(
                    font_family, font_size, is_bold=is_bold, is_italic=is_italic, text=text
                )

            # 计算文本位置
            bbox = draw.textbbox((0, 0), text, font=font)
            text_sz = (bbox[2] - bbox[0], bbox[3] - bbox[1])
            pos = self._calc_pos_by_setting(image.size, text_sz)

            # 颜色和透明度，与预览一致
            base_color = wm.get('font_color', (255,255,255,180))
            color = (base_color[0], base_color[1], base_color[2], int(255 * opacity / 100))

            # 阴影（与预览一致）
            if wm.get('has_shadow', False):
                shadow_color = (0, 0, 0, color[3] // 2)
                draw.text((pos[0] + 2, pos[1] + 2), text, font=font, fill=shadow_color)

            # 伪粗体
            if is_bold and not has_real_bold:
                for dx, dy in [(0,0), (1,0), (0,1), (1,1)]:
                    draw.text((pos[0]+dx, pos[1]+dy), text, font=font, fill=color)
            else:
                draw.text(pos, text, font=font, fill=color)

        # 合并
        result = Image.alpha_composite(image, watermark)
        return result

    def _calc_pos_by_setting(self, image_size, overlay_size):
        # 优先使用自定义位置
        custom_pos = self.settings['watermark_settings'].get('custom_position')
        if custom_pos:
            # 将预览坐标转换为原图坐标
            return self._preview_to_image_coords(custom_pos, image_size, overlay_size)
            
        # 使用预设位置
        img_w, img_h = image_size
        w, h = overlay_size
        margin = 20
        pos_key = self.settings['watermark_settings'].get('position', 'bottom_right')
        if pos_key == 'top_left':
            return (margin, margin)
        if pos_key == 'top_center':
            return ((img_w - w) // 2, margin)
        if pos_key == 'top_right':
            return (img_w - w - margin, margin)
        if pos_key == 'middle_left':
            return (margin, (img_h - h) // 2)
        if pos_key == 'center':
            return ((img_w - w) // 2, (img_h - h) // 2)
        if pos_key == 'middle_right':
            return (img_w - w - margin, (img_h - h) // 2)
        if pos_key == 'bottom_left':
            return (margin, img_h - h - margin)
        if pos_key == 'bottom_center':
            return ((img_w - w) // 2, img_h - h - margin)
        return (img_w - w - margin, img_h - h - margin)
        
    def _preview_to_image_coords(self, preview_pos, image_size, overlay_size):
        """将预览坐标转换为原图坐标（导出线程用）"""
        try:
            img_width, img_height = image_size
            # 假设预览区域为 400x300（与主界面一致）
            preview_width = 400
            preview_height = 300
            
            # 计算缩放比例
            scale_x = preview_width / img_width
            scale_y = preview_height / img_height
            scale = min(scale_x, scale_y)
            
            # 计算原图坐标
            img_x = int(preview_pos[0] / scale)
            img_y = int(preview_pos[1] / scale)
            
            # 确保不超出图片边界
            wm_width, wm_height = overlay_size
            img_x = max(0, min(img_x, img_width - wm_width))
            img_y = max(0, min(img_y, img_height - wm_height))
            
            return (img_x, img_y)
        except Exception:
            return (20, 20)  # 默认位置
        
    def generate_output_filename(self, original_path):
        """生成输出文件名"""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        ext = os.path.splitext(original_path)[1].lower()
        
        # 根据输出格式调整扩展名
        if self.settings['format'] == 'JPEG':
            if ext in ['.png', '.bmp', '.tiff', '.tif']:
                ext = '.jpg'
        elif self.settings['format'] == 'PNG':
            ext = '.png'
            
        # 根据命名规则处理
        naming_rule = self.settings['naming_rule']
        if naming_rule == "添加前缀":
            prefix = self.settings['prefix']
            return f"{prefix}{base_name}{ext}"
        elif naming_rule == "添加后缀":
            suffix = self.settings['suffix']
            return f"{base_name}{suffix}{ext}"
        else:  # 原文件名
            return f"{base_name}{ext}"

class WatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.image_list = []
        self.watermark_settings = {
            'text': '水印文字',
            'font_family': 'Microsoft YaHei',
            'font_size': 24,
            'font_color': (255, 255, 255, 180),
            'position': 'bottom_right',
            'opacity': 70,
            'rotation': 0,
            'is_bold': False,
            'is_italic': False,
            'has_shadow': False,
            'shadow_color': (0, 0, 0, 100),
            'shadow_offset': (2, 2),
            'custom_position': None  # (x, y) 自定义位置，优先级高于 position
        }
        self.templates = {}
        self.init_ui()
        self.load_templates()
        
    def init_ui(self):
        self.setWindowTitle('水印文件处理工具')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 文件列表和导入
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 中间面板 - 预览区域
        middle_panel = self.create_middle_panel()
        splitter.addWidget(middle_panel)
        
        # 右侧面板 - 水印设置
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([300, 500, 400])
        
        # 创建状态栏
        self.statusBar().showMessage('就绪')
        
    def resizeEvent(self, event):
        """窗口尺寸变化时，重新计算预览缩放，保证字号变化可见"""
        super().resizeEvent(event)
        # 仅当有当前图片时刷新
        if self.current_image:
            self.update_preview()

    def create_left_panel(self):
        """创建左侧文件管理面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 导入按钮组
        import_group = QGroupBox("导入图片")
        import_layout = QVBoxLayout(import_group)
        
        # 单张图片导入
        single_btn = QPushButton("选择单张图片")
        single_btn.clicked.connect(self.import_single_image)
        import_layout.addWidget(single_btn)
        
        # 批量导入
        batch_btn = QPushButton("批量导入图片")
        batch_btn.clicked.connect(self.import_batch_images)
        import_layout.addWidget(batch_btn)
        
        # 导入文件夹
        folder_btn = QPushButton("导入文件夹")
        folder_btn.clicked.connect(self.import_folder)
        import_layout.addWidget(folder_btn)
        
        layout.addWidget(import_group)
        
        # 图片列表
        list_group = QGroupBox("图片列表")
        list_layout = QVBoxLayout(list_group)
        
        self.image_list_widget = QListWidget()
        self.image_list_widget.itemClicked.connect(self.on_image_selected)
        list_layout.addWidget(self.image_list_widget)
        
        # 清空列表按钮
        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_image_list)
        list_layout.addWidget(clear_btn)
        
        layout.addWidget(list_group)
        
        # 导出设置
        export_group = QGroupBox("导出设置")
        export_layout = QVBoxLayout(export_group)
        
        # 输出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG"])
        format_layout.addWidget(self.format_combo)
        export_layout.addLayout(format_layout)
        
        # 输出文件夹
        folder_layout = QHBoxLayout()
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("选择输出文件夹...")
        folder_layout.addWidget(self.output_folder_edit)
        self.select_output_btn = QPushButton("选择")
        self.select_output_btn.clicked.connect(self.select_output_folder)
        folder_layout.addWidget(self.select_output_btn)
        export_layout.addLayout(folder_layout)
        
        # 文件命名
        naming_layout = QHBoxLayout()
        naming_layout.addWidget(QLabel("命名规则:"))
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["原文件名", "添加前缀", "添加后缀"])
        naming_layout.addWidget(self.naming_combo)
        export_layout.addLayout(naming_layout)
        
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("前缀 (如: wm_)")
        self.prefix_edit.setVisible(False)
        export_layout.addWidget(self.prefix_edit)
        
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("后缀 (如: _watermarked)")
        self.suffix_edit.setVisible(False)
        export_layout.addWidget(self.suffix_edit)
        
        self.naming_combo.currentTextChanged.connect(self.on_naming_changed)
        
        # 质量设置
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("质量:"))
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(90)
        self.quality_slider.setVisible(False)
        quality_layout.addWidget(self.quality_slider)
        self.quality_label = QLabel("90")
        self.quality_label.setVisible(False)
        quality_layout.addWidget(self.quality_label)
        export_layout.addLayout(quality_layout)
        
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)
        
        # 导出按钮
        export_btn = QPushButton("开始导出")
        export_btn.clicked.connect(self.export_images)
        export_layout.addWidget(export_btn)
        
        layout.addWidget(export_group)
        
        return panel
        
    def create_middle_panel(self):
        """创建中间预览面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 预览标题
        layout.addWidget(QLabel("预览"))
        
        # 预览区域
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.preview_label.setText("请选择图片进行预览")
        self.preview_label.setAcceptDrops(True)
        self.preview_label.mousePressEvent = self.on_preview_click
        self.preview_label.mouseMoveEvent = self.on_preview_drag
        self.preview_label.mouseReleaseEvent = self.on_preview_release
        self.preview_label.setMouseTracking(True)
        
        # 拖拽状态
        self.dragging = False
        self.drag_start_pos = None
        self.original_watermark_pos = None
        
        # 使预览区域可滚动
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.preview_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 水印位置控制
        position_group = QGroupBox("水印位置")
        position_layout = QGridLayout(position_group)
        
        # 九宫格位置按钮
        positions = [
            ("左上", "top_left"), ("上中", "top_center"), ("右上", "top_right"),
            ("左中", "middle_left"), ("居中", "center"), ("右中", "middle_right"),
            ("左下", "bottom_left"), ("下中", "bottom_center"), ("右下", "bottom_right")
        ]
        
        for i, (text, pos) in enumerate(positions):
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, p=pos: self.set_watermark_position(p))
            position_layout.addWidget(btn, i // 3, i % 3)
        
        layout.addWidget(position_group)
        
        return panel
        
    def create_right_panel(self):
        """创建右侧水印设置面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # 水印类型选择
        type_group = QGroupBox("水印类型")
        type_layout = QVBoxLayout(type_group)
        
        self.watermark_type_combo = QComboBox()
        self.watermark_type_combo.addItems(["文本水印", "图片水印"])
        self.watermark_type_combo.currentTextChanged.connect(self.on_watermark_type_changed)
        type_layout.addWidget(self.watermark_type_combo)
        
        layout.addWidget(type_group)
        
        # 文本水印设置
        self.text_group = QGroupBox("文本水印设置")
        text_layout = QVBoxLayout(self.text_group)
        
        # 文本内容
        text_content_layout = QHBoxLayout()
        text_content_layout.addWidget(QLabel("文本内容:"))
        self.text_edit = QLineEdit()
        self.text_edit.setText("水印文字")
        self.text_edit.textChanged.connect(self.update_preview)
        text_content_layout.addWidget(self.text_edit)
        text_layout.addLayout(text_content_layout)
        
        # 字体设置
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("字体:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Microsoft YaHei", "SimSun", "Arial", "Times New Roman"])
        self.font_combo.setCurrentText("Microsoft YaHei")
        self.font_combo.currentTextChanged.connect(self.update_preview)
        font_layout.addWidget(self.font_combo)
        text_layout.addLayout(font_layout)
        
        # 字体大小
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.setValue(24)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        size_layout.addWidget(self.font_size_spin)
        text_layout.addLayout(size_layout)
        
        # 字体样式
        style_layout = QHBoxLayout()
        self.bold_check = QCheckBox("粗体")
        self.bold_check.toggled.connect(self.update_preview)
        self.italic_check = QCheckBox("斜体")
        self.italic_check.toggled.connect(self.update_preview)
        self.shadow_check = QCheckBox("阴影")
        self.shadow_check.toggled.connect(self.update_preview)
        style_layout.addWidget(self.bold_check)
        style_layout.addWidget(self.italic_check)
        style_layout.addWidget(self.shadow_check)
        text_layout.addLayout(style_layout)
        
        # 颜色设置
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("颜色:"))
        self.color_btn = QPushButton("选择颜色")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        text_layout.addLayout(color_layout)
        
        # 透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(70)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("70%")
        opacity_layout.addWidget(self.opacity_label)
        text_layout.addLayout(opacity_layout)
        
        layout.addWidget(self.text_group)
        
        # 图片水印设置
        self.image_group = QGroupBox("图片水印设置")
        image_layout = QVBoxLayout(self.image_group)
        
        # 选择图片
        select_image_layout = QHBoxLayout()
        self.image_path_edit = QLineEdit()
        self.image_path_edit.setPlaceholderText("选择水印图片...")
        select_image_layout.addWidget(self.image_path_edit)
        self.select_image_btn = QPushButton("选择")
        self.select_image_btn.clicked.connect(self.select_watermark_image)
        select_image_layout.addWidget(self.select_image_btn)
        image_layout.addLayout(select_image_layout)
        
        # 图片透明度
        image_opacity_layout = QHBoxLayout()
        image_opacity_layout.addWidget(QLabel("透明度:"))
        self.image_opacity_slider = QSlider(Qt.Horizontal)
        self.image_opacity_slider.setRange(0, 100)
        self.image_opacity_slider.setValue(70)
        self.image_opacity_slider.valueChanged.connect(self.on_image_opacity_changed)
        image_opacity_layout.addWidget(self.image_opacity_slider)
        self.image_opacity_label = QLabel("70%")
        image_opacity_layout.addWidget(self.image_opacity_label)
        image_layout.addLayout(image_opacity_layout)
        
        self.image_group.setVisible(False)
        layout.addWidget(self.image_group)
        
        # 模板管理
        template_group = QGroupBox("模板管理")
        template_layout = QVBoxLayout(template_group)
        
        # 保存模板
        save_template_layout = QHBoxLayout()
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("模板名称...")
        save_template_layout.addWidget(self.template_name_edit)
        self.save_template_btn = QPushButton("保存")
        self.save_template_btn.clicked.connect(self.save_template)
        save_template_layout.addWidget(self.save_template_btn)
        template_layout.addLayout(save_template_layout)
        
        # 加载模板
        load_template_layout = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self.load_template)
        load_template_layout.addWidget(self.template_combo)
        self.delete_template_btn = QPushButton("删除")
        self.delete_template_btn.clicked.connect(self.delete_template)
        load_template_layout.addWidget(self.delete_template_btn)
        template_layout.addLayout(load_template_layout)
        
        layout.addWidget(template_group)
        
        return panel
        
    def import_single_image(self):
        """导入单张图片"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;所有文件 (*)",
            options=options
        )
        if file_path:
            self.add_image_to_list(file_path)
            
    def import_batch_images(self):
        """批量导入图片"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择多张图片", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;所有文件 (*)",
            options=options
        )
        for file_path in file_paths:
            self.add_image_to_list(file_path)
            
    def import_folder(self):
        """导入文件夹"""
        options = QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", "", options)
        if folder_path:
            supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        file_path = os.path.join(root, file)
                        self.add_image_to_list(file_path)
                        
    def add_image_to_list(self, file_path):
        """添加图片到列表"""
        if file_path not in self.image_list:
            self.image_list.append(file_path)
            
            # 创建列表项
            item = QListWidgetItem()
            item.setText(os.path.basename(file_path))
            item.setData(Qt.UserRole, file_path)
            
            # 创建缩略图
            try:
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    # 缩放缩略图
                    scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(scaled_pixmap))
            except Exception as e:
                print(f"创建缩略图失败: {e}")
                
            self.image_list_widget.addItem(item)
            self.statusBar().showMessage(f"已添加 {len(self.image_list)} 张图片")
            
    def clear_image_list(self):
        """清空图片列表"""
        self.image_list_widget.clear()
        self.image_list.clear()
        self.current_image = None
        self.preview_label.setText("请选择图片进行预览")
        self.statusBar().showMessage("已清空图片列表")
        
    def on_image_selected(self, item):
        """选择图片时的处理"""
        file_path = item.data(Qt.UserRole)
        self.current_image = file_path
        self.update_preview()
        
    def update_preview(self):
        """更新预览"""
        if not self.current_image:
            return
            
        try:
            # 加载原图
            image = Image.open(self.current_image)
            
            # 添加水印
            watermarked_image = self.add_watermark_to_image(image)
            
            # 转换为QPixmap显示
            if watermarked_image.mode == 'RGBA':
                # 处理透明通道
                rgb_image = Image.new('RGB', watermarked_image.size, (255, 255, 255))
                rgb_image.paste(watermarked_image, mask=watermarked_image.split()[-1])
                watermarked_image = rgb_image
            elif watermarked_image.mode != 'RGB':
                watermarked_image = watermarked_image.convert('RGB')
                
            # 转换为QImage
            width, height = watermarked_image.size
            bytes_per_line = 3 * width
            q_image = QImage(watermarked_image.tobytes(), width, height, bytes_per_line, QImage.Format_RGB888)
            
            # 缩放以适应预览区域大小
            pixmap = QPixmap.fromImage(q_image)
            target_w = max(self.preview_label.width(), 400)
            target_h = max(self.preview_label.height(), 300)
            scaled_pixmap = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            self.preview_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            QMessageBox.warning(self, "预览错误", f"无法预览图片: {str(e)}")
            
    def add_watermark_to_image(self, image):
        """为图片添加水印"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
            
        # 创建水印层
        watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        watermark_type = self.watermark_type_combo.currentText()
        
        if watermark_type == "文本水印":
            self.add_text_watermark(draw, image.size)
        elif watermark_type == "图片水印":
            self.add_image_watermark(watermark, image.size)
            
        # 合并水印和原图
        result = Image.alpha_composite(image, watermark)
        return result
        
    def add_text_watermark(self, draw, image_size):
        """添加文本水印"""
        text = self.text_edit.text()
        if not text:
            return
            
        # 获取字体
        font_size = self.font_size_spin.value()
        font_family = self.font_combo.currentText()
        font, has_real_bold, has_real_italic = self.get_pil_font(
            font_family,
            font_size,
            is_bold=self.bold_check.isChecked(),
            is_italic=self.italic_check.isChecked(),
            text=text,
        )
            
        # 计算文本位置
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 根据位置设置计算坐标
        position = self.get_watermark_position(image_size, (text_width, text_height))
        
        # 获取颜色和透明度
        color = self.get_text_color()
        
        # 添加阴影
        if self.shadow_check.isChecked():
            shadow_color = (0, 0, 0, color[3] // 2)
            draw.text((position[0] + 2, position[1] + 2), text, font=font, fill=shadow_color)
            
        # 绘制文本（如无真实粗体则用伪粗体叠描）
        if self.bold_check.isChecked() and not has_real_bold:
            for dx, dy in [(0,0), (1,0), (0,1), (1,1)]:
                draw.text((position[0]+dx, position[1]+dy), text, font=font, fill=color)
        else:
            draw.text(position, text, font=font, fill=color)
        
    def get_pil_font(self, family: str, size: int, is_bold: bool = False, is_italic: bool = False, text: str = ""):
        """返回字体对象及是否为真实粗体/斜体。(font, has_real_bold, has_real_italic)
        优先匹配常见字体文件；若缺少对应字形，则回退到常规文件，并由调用方决定是否伪粗体。
        """
        try:
            fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            # 映射: 常规, 粗体, 斜体, 粗斜体
            mapping = {
                'Microsoft YaHei': ('msyh.ttc', 'msyhbd.ttc', None, None),
                'SimSun': ('simsun.ttc', None, None, None),
                'SimHei': ('simhei.ttf', None, None, None),
                'Arial': ('arial.ttf', 'arialbd.ttf', 'ariali.ttf', 'arialbi.ttf'),
                'Times New Roman': ('times.ttf', 'timesbd.ttf', 'timesi.ttf', 'timesbi.ttf'),
            }

            def select_variant(fam: str):
                reg, bold, italic, bolditalic = mapping.get(fam, (None, None, None, None))
                if is_bold and is_italic and bolditalic:
                    return bolditalic, True, True
                if is_bold and bold:
                    return bold, True, False
                if is_italic and italic:
                    return italic, False, True
                return reg, False, False

            # 若文本含中日韩字符，优先中文字体
            def has_cjk(s: str) -> bool:
                for ch in s:
                    code = ord(ch)
                    if (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF) or (0x20000 <= code <= 0x2A6DF):
                        return True
                return False

            search_order = []
            if has_cjk(text):
                search_order.extend(['Microsoft YaHei', 'SimSun', 'SimHei'])
            if family not in search_order:
                search_order.insert(0, family)

            tried = set()
            for fam in search_order:
                fname, real_bold, real_italic = select_variant(fam)
                if not fname:
                    continue
                fpath = os.path.join(fonts_dir, fname)
                if fpath in tried:
                    continue
                tried.add(fpath)
                if os.path.exists(fpath):
                    # 记录解析到的字体文件，供导出线程复用
                    try:
                        self.watermark_settings['resolved_font_path'] = fpath
                    except Exception:
                        pass
                    return ImageFont.truetype(fpath, size=size), real_bold, real_italic

            # 最后尝试家族名解析
            try:
                return ImageFont.truetype(family, size=size), False, False
            except Exception:
                return ImageFont.load_default(), False, False
        except Exception:
            return ImageFont.load_default(), False, False

    def add_image_watermark(self, watermark_layer, image_size):
        """添加图片水印"""
        image_path = self.image_path_edit.text()
        if not image_path or not os.path.exists(image_path):
            return
            
        try:
            # 加载水印图片
            wm_image = Image.open(image_path)
            if wm_image.mode != 'RGBA':
                wm_image = wm_image.convert('RGBA')
                
            # 调整透明度
            opacity = self.image_opacity_slider.value() / 100.0
            if opacity < 1.0:
                wm_image = ImageEnhance.Brightness(wm_image).enhance(opacity)
                # 调整alpha通道
                alpha = wm_image.split()[-1]
                alpha = alpha.point(lambda p: int(p * opacity))
                wm_image.putalpha(alpha)
                
            # 计算位置和大小
            wm_size = wm_image.size
            position = self.get_watermark_position(image_size, wm_size)
            
            # 粘贴水印图片
            watermark_layer.paste(wm_image, position, wm_image)
            
        except Exception as e:
            print(f"添加图片水印失败: {e}")
            
    def get_watermark_position(self, image_size, watermark_size):
        """计算水印位置"""
        # 优先使用自定义位置
        custom_pos = self.watermark_settings.get('custom_position')
        if custom_pos:
            # 将预览坐标转换为原图坐标
            return self.preview_to_image_coords(custom_pos, image_size, watermark_size)
            
        # 使用预设位置
        img_width, img_height = image_size
        wm_width, wm_height = watermark_size
        margin = 20
        
        if self.watermark_settings['position'] == 'top_left':
            return (margin, margin)
        elif self.watermark_settings['position'] == 'top_center':
            return ((img_width - wm_width) // 2, margin)
        elif self.watermark_settings['position'] == 'top_right':
            return (img_width - wm_width - margin, margin)
        elif self.watermark_settings['position'] == 'middle_left':
            return (margin, (img_height - wm_height) // 2)
        elif self.watermark_settings['position'] == 'center':
            return ((img_width - wm_width) // 2, (img_height - wm_height) // 2)
        elif self.watermark_settings['position'] == 'middle_right':
            return (img_width - wm_width - margin, (img_height - wm_height) // 2)
        elif self.watermark_settings['position'] == 'bottom_left':
            return (margin, img_height - wm_height - margin)
        elif self.watermark_settings['position'] == 'bottom_center':
            return ((img_width - wm_width) // 2, img_height - wm_height - margin)
        elif self.watermark_settings['position'] == 'bottom_right':
            return (img_width - wm_width - margin, img_height - wm_height - margin)
        else:
            return (margin, margin)
            
    def preview_to_image_coords(self, preview_pos, image_size, watermark_size):
        """将预览坐标转换为原图坐标"""
        try:
            img_width, img_height = image_size
            preview_width = self.preview_label.width()
            preview_height = self.preview_label.height()
            
            # 计算缩放比例
            scale_x = preview_width / img_width
            scale_y = preview_height / img_height
            scale = min(scale_x, scale_y)
            
            # 计算原图坐标
            img_x = int(preview_pos[0] / scale)
            img_y = int(preview_pos[1] / scale)
            
            # 确保不超出图片边界
            wm_width, wm_height = watermark_size
            img_x = max(0, min(img_x, img_width - wm_width))
            img_y = max(0, min(img_y, img_height - wm_height))
            
            return (img_x, img_y)
        except Exception:
            return (20, 20)  # 默认位置
            
    def get_text_color(self):
        """获取文本颜色"""
        # 使用设置的颜色和透明度
        base_color = self.watermark_settings.get('font_color', (255, 255, 255, 180))
        opacity = self.opacity_slider.value()
        return (base_color[0], base_color[1], base_color[2], int(255 * opacity / 100))
        
    def set_watermark_position(self, position):
        """设置水印位置"""
        self.watermark_settings['position'] = position
        # 清除自定义位置，使用预设位置
        self.watermark_settings['custom_position'] = None
        self.update_preview()
        
    def choose_color(self):
        """选择颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            # 保存颜色设置
            self.watermark_settings['font_color'] = (color.red(), color.green(), color.blue(), 180)
            self.statusBar().showMessage(f"已选择颜色: {color.name()}")
            self.update_preview()
            
    def on_preview_click(self, event):
        """预览区域点击事件"""
        if not self.current_image:
            return
            
        if event.button() == Qt.LeftButton:
            # 检查是否点击在水印区域
            if self.is_click_on_watermark(event.pos()):
                # 开始拖拽
                self.dragging = True
                self.drag_start_pos = event.pos()
                self.original_watermark_pos = self.watermark_settings.get('custom_position')
                self.preview_label.setCursor(Qt.ClosedHandCursor)
            else:
                # 切换水印位置
                positions = ['top_left', 'top_center', 'top_right', 
                           'middle_left', 'center', 'middle_right',
                           'bottom_left', 'bottom_center', 'bottom_right']
                current_pos = self.watermark_settings['position']
                try:
                    current_index = positions.index(current_pos)
                    next_index = (current_index + 1) % len(positions)
                    self.watermark_settings['position'] = positions[next_index]
                    # 清除自定义位置，使用预设位置
                    self.watermark_settings['custom_position'] = None
                    self.update_preview()
                except ValueError:
                    self.watermark_settings['position'] = 'bottom_right'
                    self.watermark_settings['custom_position'] = None
                    self.update_preview()
                    
    def on_preview_drag(self, event):
        """预览区域拖拽事件"""
        if not self.dragging or not self.current_image:
            return
            
        # 计算拖拽偏移
        delta = event.pos() - self.drag_start_pos
        if self.original_watermark_pos:
            new_pos = (self.original_watermark_pos[0] + delta.x(), 
                      self.original_watermark_pos[1] + delta.y())
        else:
            # 从当前位置计算
            current_pos = self.get_current_watermark_position()
            new_pos = (current_pos[0] + delta.x(), current_pos[1] + delta.y())
            
        # 更新自定义位置
        self.watermark_settings['custom_position'] = new_pos
        self.update_preview()
        
    def on_preview_release(self, event):
        """预览区域释放事件"""
        if self.dragging:
            self.dragging = False
            self.drag_start_pos = None
            self.original_watermark_pos = None
            self.preview_label.setCursor(Qt.ArrowCursor)
            
    def is_click_on_watermark(self, click_pos):
        """检查点击位置是否在水印区域"""
        if not self.current_image:
            return False
            
        try:
            # 获取当前水印位置和大小
            current_pos = self.get_current_watermark_position()
            if not current_pos:
                return False
                
            # 计算水印区域（简化：假设水印区域为 100x30 像素）
            watermark_rect = QRect(current_pos[0], current_pos[1], 100, 30)
            return watermark_rect.contains(click_pos)
        except Exception:
            return False
            
    def get_current_watermark_position(self):
        """获取当前水印在预览图中的位置"""
        if not self.current_image:
            return None
            
        try:
            # 加载原图获取尺寸
            image = Image.open(self.current_image)
            img_width, img_height = image.size
            
            # 计算预览缩放比例
            preview_width = self.preview_label.width()
            preview_height = self.preview_label.height()
            scale_x = preview_width / img_width
            scale_y = preview_height / img_height
            scale = min(scale_x, scale_y)
            
            # 计算水印在预览中的位置
            if self.watermark_settings.get('custom_position'):
                return self.watermark_settings['custom_position']
            else:
                # 使用预设位置计算
                position = self.watermark_settings['position']
                margin = 20
                
                if position == 'top_left':
                    return (margin, margin)
                elif position == 'top_center':
                    return (preview_width // 2 - 50, margin)
                elif position == 'top_right':
                    return (preview_width - 100 - margin, margin)
                elif position == 'middle_left':
                    return (margin, preview_height // 2 - 15)
                elif position == 'center':
                    return (preview_width // 2 - 50, preview_height // 2 - 15)
                elif position == 'middle_right':
                    return (preview_width - 100 - margin, preview_height // 2 - 15)
                elif position == 'bottom_left':
                    return (margin, preview_height - 30 - margin)
                elif position == 'bottom_center':
                    return (preview_width // 2 - 50, preview_height - 30 - margin)
                elif position == 'bottom_right':
                    return (preview_width - 100 - margin, preview_height - 30 - margin)
                else:
                    return (margin, margin)
        except Exception:
            return None
            
    def on_opacity_changed(self, value):
        """透明度改变"""
        self.opacity_label.setText(f"{value}%")
        self.update_preview()
        
    def on_image_opacity_changed(self, value):
        """图片透明度改变"""
        self.image_opacity_label.setText(f"{value}%")
        self.update_preview()
        
    def on_watermark_type_changed(self, text):
        """水印类型改变"""
        if text == "文本水印":
            self.text_group.setVisible(True)
            self.image_group.setVisible(False)
        else:
            self.text_group.setVisible(False)
            self.image_group.setVisible(True)
        self.update_preview()
        
    def select_watermark_image(self):
        """选择水印图片"""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择水印图片", "", 
            "图片文件 (*.png *.jpg *.jpeg);;所有文件 (*)",
            options=options
        )
        if file_path:
            self.image_path_edit.setText(file_path)
            self.update_preview()
            
    def select_output_folder(self):
        """选择输出文件夹"""
        options = QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
        folder_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹", "", options)
        if folder_path:
            self.output_folder_edit.setText(folder_path)
            
    def on_naming_changed(self, text):
        """命名规则改变"""
        if text == "添加前缀":
            self.prefix_edit.setVisible(True)
            self.suffix_edit.setVisible(False)
        elif text == "添加后缀":
            self.prefix_edit.setVisible(False)
            self.suffix_edit.setVisible(True)
        else:
            self.prefix_edit.setVisible(False)
            self.suffix_edit.setVisible(False)
            
    def on_format_changed(self, format_text):
        """输出格式改变"""
        if format_text == "JPEG":
            self.quality_slider.setVisible(True)
            self.quality_label.setVisible(True)
        else:
            self.quality_slider.setVisible(False)
            self.quality_label.setVisible(False)
            
    def on_quality_changed(self, value):
        """质量设置改变"""
        self.quality_label.setText(str(value))
        
    def export_images(self):
        """导出图片"""
        if not self.image_list:
            QMessageBox.warning(self, "警告", "请先导入图片")
            return
            
        output_folder = self.output_folder_edit.text()
        if not output_folder:
            QMessageBox.warning(self, "警告", "请选择输出文件夹")
            return
            
        # 同步最新的界面设置到 watermark_settings，避免导出读取旧值（如字号/字体）
        self.update_current_settings()

        # 检查输出文件夹是否为原文件夹
        for image_path in self.image_list:
            if os.path.dirname(os.path.abspath(image_path)) == os.path.abspath(output_folder):
                QMessageBox.warning(self, "警告", "不能导出到原文件夹，请选择其他文件夹")
                return
        
        # 创建导出线程
        self.export_thread = ExportThread(self.image_list, output_folder, self.get_export_settings())
        self.export_thread.progress_updated.connect(self.on_export_progress)
        self.export_thread.finished.connect(self.on_export_finished)
        self.export_thread.start()
        
        # 显示进度对话框（非阻塞）
        from PyQt5.QtWidgets import QProgressDialog
        self.progress_dialog = QProgressDialog("正在导出图片...", None, 0, len(self.image_list), self)
        self.progress_dialog.setWindowTitle("导出进度")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()
        
    def get_export_settings(self):
        """获取导出设置"""
        s = {
            'format': self.format_combo.currentText(),
            'quality': self.quality_slider.value(),
            'naming_rule': self.naming_combo.currentText(),
            'prefix': self.prefix_edit.text(),
            'suffix': self.suffix_edit.text(),
            'watermark_settings': self.watermark_settings.copy(),
            'watermark_type': self.watermark_type_combo.currentText(),
            'image_watermark_path': self.image_path_edit.text(),
            'image_watermark_opacity': self.image_opacity_slider.value()
        }
        # 如果已经解析过字体文件路径，则一并传给导出线程，避免导出时找不到字体导致方框
        resolved_font = self.watermark_settings.get('resolved_font_path')
        if resolved_font:
            s['resolved_font_path'] = resolved_font
        return s
        
    def on_export_progress(self, current, total, filename):
        """导出进度更新"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(f"正在导出图片... ({current}/{total})\n当前文件: {filename}")
            # 进度以当前索引设置
            self.progress_dialog.setMaximum(total)
            self.progress_dialog.setValue(current)
            
    def on_export_finished(self, success_count, error_count, errors):
        """导出完成"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(self.progress_dialog.maximum())
            self.progress_dialog.close()
            self.progress_dialog = None
            
        if error_count == 0:
            QMessageBox.information(self, "导出完成", f"成功导出 {success_count} 张图片")
        else:
            error_msg = f"成功导出 {success_count} 张图片\n失败 {error_count} 张图片"
            if errors:
                error_msg += f"\n\n错误详情:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"\n... 还有 {len(errors) - 5} 个错误"
            QMessageBox.warning(self, "导出完成", error_msg)
        
    def save_template(self):
        """保存模板"""
        template_name = self.template_name_edit.text().strip()
        if not template_name:
            QMessageBox.warning(self, "警告", "请输入模板名称")
            return
            
        # 更新当前设置
        self.update_current_settings()
        
        # 保存当前设置到模板
        self.templates[template_name] = self.watermark_settings.copy()
        self.save_templates()
        self.update_template_combo()
        self.template_name_edit.clear()
        QMessageBox.information(self, "成功", f"模板 '{template_name}' 已保存")
        
    def update_current_settings(self):
        """更新当前设置"""
        self.watermark_settings.update({
            'text': self.text_edit.text(),
            'font_family': self.font_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'opacity': self.opacity_slider.value(),
            'is_bold': self.bold_check.isChecked(),
            'is_italic': self.italic_check.isChecked(),
            'has_shadow': self.shadow_check.isChecked()
        })
        
    def load_template(self, template_name):
        """加载模板"""
        if template_name and template_name in self.templates:
            self.watermark_settings.update(self.templates[template_name])
            # 更新UI控件
            self.update_ui_from_settings()
            self.update_preview()
            
    def update_ui_from_settings(self):
        """从设置更新UI"""
        settings = self.watermark_settings
        
        # 更新文本设置
        self.text_edit.setText(settings.get('text', '水印文字'))
        self.font_combo.setCurrentText(settings.get('font_family', 'Microsoft YaHei'))
        self.font_size_spin.setValue(settings.get('font_size', 24))
        self.opacity_slider.setValue(settings.get('opacity', 70))
        self.opacity_label.setText(f"{settings.get('opacity', 70)}%")
        
        # 更新样式设置
        self.bold_check.setChecked(settings.get('is_bold', False))
        self.italic_check.setChecked(settings.get('is_italic', False))
        self.shadow_check.setChecked(settings.get('has_shadow', False))
            
    def delete_template(self):
        """删除模板"""
        template_name = self.template_combo.currentText()
        if template_name and template_name in self.templates:
            reply = QMessageBox.question(self, "确认", f"确定要删除模板 '{template_name}' 吗？")
            if reply == QMessageBox.Yes:
                del self.templates[template_name]
                self.save_templates()
                self.update_template_combo()
                
    def update_template_combo(self):
        """更新模板下拉框"""
        self.template_combo.clear()
        self.template_combo.addItems(list(self.templates.keys()))
        
    def update_ui_from_settings(self):
        """从设置更新UI"""
        # 这里应该根据watermark_settings更新各个UI控件
        pass
        
    def save_templates(self):
        """保存模板到文件"""
        try:
            with open('templates.json', 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模板失败: {e}")
            
    def load_templates(self):
        """从文件加载模板"""
        try:
            if os.path.exists('templates.json'):
                with open('templates.json', 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)
                self.update_template_combo()
        except Exception as e:
            print(f"加载模板失败: {e}")

def main():
    _ensure_qt_plugin_env()
    app = QApplication(sys.argv)
    window = WatermarkApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()