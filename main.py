import sys
from PyQt6.QtWidgets import QApplication
from gui import MainWindow
from image_processor import ImageProcessor

def main():
    """
    主程序入口
    """
    app = QApplication(sys.argv)
    
    # 创建图像处理器
    processor = ImageProcessor()
    
    # 创建主窗口
    window = MainWindow(processor)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 