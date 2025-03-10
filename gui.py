from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QCheckBox)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor
import cv2
import numpy as np

class MainWindow(QMainWindow):
    """
    主窗口类
    """
    
    def __init__(self, image_processor):
        """
        初始化主窗口
        
        @param image_processor: ImageProcessor 图像处理器实例
        """
        super().__init__()
        self.image_processor = image_processor
        self.current_image = None
        self.drawing = False
        self.mask_points = []  # 存储绘制的点
        self.use_manual_mask = False
        
        self.setWindowTitle("证件照背景更换工具")
        self.setMinimumSize(800, 600)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        self.upload_btn = QPushButton("上传图片")
        self.blue_bg_btn = QPushButton("蓝色背景")
        self.gray_bg_btn = QPushButton("灰色背景")
        self.save_btn = QPushButton("保存图片")
        self.clear_mask_btn = QPushButton("清除绘制")
        
        # 添加复选框
        self.draw_mode_cb = QCheckBox("启用绘制模式")
        self.draw_mode_cb.setChecked(False)
        
        button_layout.addWidget(self.upload_btn)
        button_layout.addWidget(self.blue_bg_btn)
        button_layout.addWidget(self.gray_bg_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.clear_mask_btn)
        button_layout.addWidget(self.draw_mode_cb)
        
        # 创建图片显示区域
        self.image_label = DrawableLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 添加到主布局
        layout.addLayout(button_layout)
        layout.addWidget(self.image_label)
        
        # 连接信号
        self.upload_btn.clicked.connect(self.upload_image)
        self.blue_bg_btn.clicked.connect(lambda: self.change_background('blue'))
        self.gray_bg_btn.clicked.connect(lambda: self.change_background('gray'))
        self.save_btn.clicked.connect(self.save_image)
        self.clear_mask_btn.clicked.connect(self.clear_mask)
        self.draw_mode_cb.stateChanged.connect(self.toggle_draw_mode)
        
        # 初始化按钮状态
        self.update_button_states(False)
        self.clear_mask_btn.setEnabled(False)

    def toggle_draw_mode(self, state):
        """切换绘制模式"""
        self.image_label.drawing_enabled = bool(state)
        if self.current_image is not None:
            self.clear_mask_btn.setEnabled(bool(state))

    def clear_mask(self):
        """清除绘制的遮罩"""
        self.image_label.clear_mask()
        if self.current_image is not None:
            self.display_image(self.current_image)

    def update_button_states(self, has_image):
        """
        更新按钮状态
        
        @param has_image: bool 是否有图片加载
        """
        self.blue_bg_btn.setEnabled(has_image)
        self.gray_bg_btn.setEnabled(has_image)
        self.save_btn.setEnabled(has_image)
        self.clear_mask_btn.setEnabled(has_image and self.draw_mode_cb.isChecked())

    def upload_image(self):
        """
        上传图片
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png)"
        )
        
        if file_name:
            self.current_image = cv2.imread(file_name)
            self.display_image(self.current_image)
            self.update_button_states(True)
            self.image_label.original_size = (self.current_image.shape[1], 
                                            self.current_image.shape[0])

    def change_background(self, bg_type):
        """
        更换背景
        
        @param bg_type: str 背景类型
        """
        if self.current_image is not None:
            # 获取用户绘制的遮罩
            manual_mask = self.image_label.get_mask(self.current_image.shape[:2])
            # 处理图像
            result = self.image_processor.change_background(
                self.current_image, 
                bg_type,
                manual_mask if self.draw_mode_cb.isChecked() else None
            )
            self.display_image(result)
            self.current_image = result

    def save_image(self):
        """
        保存图片
        """
        if self.current_image is not None:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "保存图片",
                "",
                "JPG 文件 (*.jpg);;PNG 文件 (*.png)"
            )
            if file_name:
                cv2.imwrite(file_name, self.current_image)

    def display_image(self, image):
        """
        显示图片，保持原始比例
        
        @param image: numpy.ndarray 要显示的图片
        """
        height, width = image.shape[:2]
        bytes_per_line = 3 * width
        
        # 转换图片格式
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        q_image = QImage(image_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # 计算缩放后的尺寸，保持原始比例
        label_size = self.image_label.size()
        scaled_pixmap = pixmap.scaled(
            label_size.width(),
            label_size.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 设置图片并禁用自动缩放
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setScaledContents(False)

class DrawableLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.drawing = False
        self.drawing_enabled = False
        self.points = []
        self.original_size = None
        
        # 设置最小尺寸
        self.setMinimumSize(400, 300)
        
    def resizeEvent(self, event):
        """
        处理窗口大小改变事件
        """
        super().resizeEvent(event)
        # 如果有图片，重新调整大小
        if self.pixmap() is not None:
            scaled_pixmap = self.pixmap().scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            super().setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        if self.drawing_enabled and event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.points.append(self.map_to_original(event.pos()))
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing and self.drawing_enabled:
            self.points.append(self.map_to_original(event.pos()))
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drawing_enabled and self.points:
            painter = QPainter(self)
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(2)
            painter.setPen(pen)
            
            # 绘制已有的点
            for i in range(len(self.points) - 1):
                p1 = self.map_from_original(self.points[i])
                p2 = self.map_from_original(self.points[i + 1])
                painter.drawLine(p1, p2)

    def map_to_original(self, pos):
        """
        将窗口坐标映射到原始图像坐标，考虑实际显示比例
        """
        if not self.original_size or not self.pixmap():
            return pos
            
        # 获取实际显示的图片区域
        pixmap_rect = self.get_pixmap_rect()
        if not pixmap_rect:
            return pos
            
        # 计算相对位置
        x_ratio = self.original_size[0] / pixmap_rect.width()
        y_ratio = self.original_size[1] / pixmap_rect.height()
        
        return QPoint(
            int((pos.x() - pixmap_rect.x()) * x_ratio),
            int((pos.y() - pixmap_rect.y()) * y_ratio)
        )

    def map_from_original(self, pos):
        """
        将原始图像坐标映射到窗口坐标，考虑实际显示比例
        """
        if not self.original_size or not self.pixmap():
            return pos
            
        # 获取实际显示的图片区域
        pixmap_rect = self.get_pixmap_rect()
        if not pixmap_rect:
            return pos
            
        # 计算相对位置
        x_ratio = pixmap_rect.width() / self.original_size[0]
        y_ratio = pixmap_rect.height() / self.original_size[1]
        
        return QPoint(
            int(pos.x() * x_ratio + pixmap_rect.x()),
            int(pos.y() * y_ratio + pixmap_rect.y())
        )

    def get_pixmap_rect(self):
        """
        获取实际显示的图片区域
        """
        if not self.pixmap():
            return None
            
        # 计算实际显示的图片区域
        pixmap_size = self.pixmap().size()
        scaled_size = pixmap_size.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        
        # 计算图片在标签中的位置（居中显示）
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        
        return QRect(x, y, scaled_size.width(), scaled_size.height())

    def clear_mask(self):
        """清除绘制的遮罩"""
        self.points = []
        self.update()

    def get_mask(self, image_size):
        """获取绘制的遮罩"""
        if not self.points:
            return None
            
        mask = np.zeros(image_size, dtype=np.uint8)
        points = np.array([(p.x(), p.y()) for p in self.points])
        
        # 绘制线条
        for i in range(len(points) - 1):
            cv2.line(mask, 
                    (int(points[i][0]), int(points[i][1])),
                    (int(points[i+1][0]), int(points[i+1][1])),
                    255, 
                    thickness=5)
        
        # 使用形态学操作填充区域
        kernel = np.ones((10,10), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        return mask 