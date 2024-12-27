import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, 
                           QVBoxLayout, QHBoxLayout, QWidget, QListWidget, QProgressBar, 
                           QLabel, QStackedWidget, QSpinBox, QFrame, QListWidgetItem, QSizePolicy, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt5.QtGui import QPalette, QFont, QIcon
from PyPDF2 import PdfReader, PdfWriter
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtCore import QSize

class NavButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QPushButton {
                border: none;
                text-align: center;
                padding: 8px 16px;
                font-size: 15px;
                color: #666666;
                background-color: #F3F4F7;
                margin: 4px 16px;
            }
            QPushButton:checked {
                color: #2B6DE8;
                font-weight: bold;
                background-color: #DFE7F4;
                border-radius: 6px;
            }
            QPushButton:hover:!checked {
                color: #2B6DE8;
                background-color: #E8E9ED;
                border-radius: 6px;
            }
        """)

class ActionButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(36)
        self.setFixedWidth(200)  # 设固定宽度
        self.setStyleSheet("""
            QPushButton {
                background-color: #4B8BF4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3B7DE8;
            }
            QPushButton:pressed {
                background-color: #2B6DD8;
            }
            QPushButton:disabled {
                background-color: rgba(75, 139, 244, 0.5);  /* 50%透明度 */
                color: rgba(255, 255, 255, 0.5);  /* 50%透明度 */
            }
        """)

class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.parent_widget = parent
        
        # 添加空状态提示标签
        self.empty_label = QLabel("将文件拖拽到此处", self)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 13px;
                background: transparent;
            }
        """)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        # 设置提示标签层级
        self.empty_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.empty_label.lower()  # 将提示标签放到底层
        
        self.default_style = """
            QListWidget {
                border: 1px solid #F7F7F7;
                border-radius: 4px;
                background-color: white;
                color: #333333;
                font-size: 13px;
                padding: 4px;
            }
            QListWidget::item {
                color: #333333;
                background-color: white;
                padding: 0px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget::item:selected {
                background-color: #EEF7FF;
                color: #333333;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
            QListWidget:focus {
                border: 1px solid #F7F7F7;
            }
        """
        self.setStyleSheet(self.default_style)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 调整提示标签位置
        self.empty_label.setGeometry(0, 0, self.width(), self.height())
        
    def showEvent(self, event):
        super().showEvent(event)
        self.updateEmptyState()
        
    def updateEmptyState(self):
        # 根据列表项数量显示或隐藏提示
        self.empty_label.setVisible(self.count() == 0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            # 不再在这里隐藏提示标签
            self.setStyleSheet("""
                QListWidget {
                    border: 2px dashed #2B6DE8;
                    border-radius: 4px;
                    background-color: #F8FBFF;
                    color: #333333;
                    font-size: 13px;
                    padding: 4px;
                }
                QListWidget::item {
                    color: #333333;
                    background-color: white;
                    padding: 0px;
                    border-bottom: 1px solid #F0F0F0;
                }
                QListWidget::item:selected {
                    background-color: #EEF7FF;
                    color: #333333;
                }
                QListWidget::item:hover {
                    background-color: #F5F5F5;
                }
            """)
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragMoveEvent(event)  # 处理内部拖拽

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.default_style)
        self.updateEmptyState()  # 恢复提示（如果列表为空）
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(self.default_style)
            # 处理文件
            if isinstance(self.parent_widget, PDFSplitWidget):
                self.parent_widget.handle_dropped_files(event.mimeData().urls())
            elif hasattr(self.parent_widget, 'handle_dropped_files'):
                self.parent_widget.handle_dropped_files(event.mimeData().urls())
            self.updateEmptyState()  # 根据列表状态显示或隐藏提示
        else:
            super().dropEvent(event)

class PDFSplitWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setup_ui()
        self.pdf_file = None
        self.max_pages = 0

    def handle_dropped_files(self, urls):
        # 只处理第一个PDF文件
        for url in urls:
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
                    self.load_pdf(file_path)
                    break  # 只处理第一个文件
                elif os.path.isdir(file_path):
                    # 处理文件夹中的第一个PDF文件
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            if file.lower().endswith('.pdf'):
                                full_path = os.path.join(root, file)
                                self.load_pdf(full_path)
                                return  # 找到第一个PDF文件后返回

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 48, 20, 20)
        layout.setSpacing(12)
        
        # 创建列表容器
        list_container = QWidget()
        list_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #F3F4F7;
                border-radius: 4px;
            }
        """)
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(4, 4, 4, 4)
        
        # 文件列表
        self.file_list = DragDropListWidget(self)
        self.file_list.setMinimumHeight(200)
        
        # 添加文件按钮
        self.add_file_button = AddFileButton()
        self.add_file_button.clicked.connect(self.select_file)
        
        list_layout.addWidget(self.file_list)
        list_layout.addWidget(self.add_file_button)
        layout.addWidget(list_container)
        
        # 提示语放在列表下方
        self.label = QLabel("添加要提取的PDF文件，提取后的PDF文件会保存至原文件夹")
        self.label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.label)
        
        # 修改页面范围设置
        range_widget = QWidget()
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(4)  # 设置组件间距
        
        self.range_label = QLabel("输入需要提取的页码：")
        self.range_label.setStyleSheet("color: #333333; font-size: 15px;")
        
        # 使用输入框替代数字选择器
        self.page_input = QLineEdit()
        self.page_input.setEnabled(False)
        self.page_input.setStyleSheet("""
            QLineEdit {
                color: #333333;
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 15px;
                min-width: 120px;
            }
            QLineEdit:disabled {
                background-color: #F5F5F5;
                color: #999999;
            }
        """)
        
        # 添加最大页码显示
        self.max_page_label = QLabel("/--")
        self.max_page_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 15px;
                padding: 0 4px;
            }
        """)
        
        # 添加范例说明
        self.example_label = QLabel("（示例：1,3,5-9）")
        self.example_label.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 13px;
                padding-left: 8px;
            }
        """)
        
        range_layout.addWidget(self.range_label)
        range_layout.addWidget(self.page_input)
        range_layout.addWidget(self.max_page_label)
        range_layout.addWidget(self.example_label)
        range_layout.addStretch()
        
        layout.addWidget(range_widget)
        
        # 底部按钮容器
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(20, 10, 20, 20)  # 增加左右边距
        
        # 按钮靠右放置
        bottom_layout.addStretch()
        self.split_button = ActionButton("提取PDF")
        self.split_button.clicked.connect(self.split_pdf)
        self.split_button.setEnabled(False)
        bottom_layout.addWidget(self.split_button)
        
        layout.addWidget(bottom_container)
        self.setLayout(layout)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择PDF文件", "", "PDF文件 (*.pdf)")
        if file:
            self.load_pdf(file)

    def load_pdf(self, file_path):
        self.pdf_file = file_path
        self.file_list.clear()
        
        # 添加带删除按钮的文件项
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 4, 12, 4)
        
        # 文件名标签
        label = QLabel(os.path.basename(file_path))
        label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 13px;
                border: none;  /* 移除边框 */
                background: transparent;  /* 透明背景 */
            }
        """)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 删除按钮
        delete_btn = DeleteButton()
        delete_btn.setFixedWidth(40)
        delete_btn.clicked.connect(lambda: self.remove_file())
        
        layout.addWidget(label)
        layout.addWidget(delete_btn)
        
        # 设置整个项目的样式
        widget.setStyleSheet("""
            QWidget {
                background: transparent;  /* 透明背景 */
                border: none;  /* 移除边框 */
            }
        """)
        
        widget.setFixedHeight(36)  # 固定每个项目的高度
        item.setSizeHint(widget.sizeHint())
        
        self.file_list.addItem(item)
        self.file_list.setItemWidget(item, widget)
        
        # 读取PDF页数
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            self.max_pages = len(pdf.pages)
        
        # 更新控件
        self.page_input.setEnabled(True)
        self.page_input.clear()
        self.max_page_label.setText(f"/{self.max_pages}页")  # 更新最大页码显示，添加“页”
        self.split_button.setEnabled(True)
        
        self.main_window.show_toast(f"PDF文件加载，共 {self.max_pages} 页")

    def remove_file(self):
        self.file_list.clear()
        self.pdf_file = None
        self.max_pages = 0
        self.page_input.setEnabled(False)
        self.page_input.clear()
        self.max_page_label.setText("/--页")  # 重置最大页码显示，添加“页”
        self.split_button.setEnabled(False)

    def parse_page_ranges(self, input_text):
        """解析页码输入"""
        try:
            pages = set()
            parts = input_text.replace(' ', '').split(',')
            
            for part in parts:
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    if start < 1 or end > self.max_pages or start > end:
                        raise ValueError
                    pages.update(range(start, end + 1))
                else:
                    page = int(part)
                    if page < 1 or page > self.max_pages:
                        raise ValueError
                    pages.add(page)
            
            return sorted(list(pages))
        except ValueError:
            return None

    def split_pdf(self):
        if not self.pdf_file:
            return
        
        input_text = self.page_input.text().strip()
        if not input_text:
            self.main_window.show_toast("请输入需要提取的页码")
            return
        
        pages = self.parse_page_ranges(input_text)
        if pages is None:
            self.main_window.show_toast("页码格式错误或超出范围")
            return
        
        # 创建输出文件名
        base_name = os.path.splitext(self.pdf_file)[0]
        page_desc = f"{pages[0]}-{pages[-1]}" if len(pages) > 1 else str(pages[0])
        output_file = f"{base_name}_提取_{page_desc}.pdf"
        
        try:
            # 提取PDF
            pdf_writer = PdfWriter()
            with open(self.pdf_file, 'rb') as file:
                pdf_reader = PdfReader(file)
                
                # 添加选定的页面
                for page_num in pages:
                    pdf_writer.add_page(pdf_reader.pages[page_num - 1])
            
            # 保存提取后的PDF
            with open(output_file, 'wb') as output:
                pdf_writer.write(output)
            
            self.main_window.show_toast("PDF提取完成，文件已保存至原文件夹")
            
        except Exception as e:
            self.main_window.show_toast("提取PDF时出错")

class AddFileButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("+ 添加文件", parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #666666;
                border: none;
                font-size: 14px;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover {
                color: #2B6DE8;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

class DeleteButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("删除", parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: none;
                font-size: 13px;
                padding: 4px 8px;
                text-align: center;
            }
            QPushButton:hover {
                color: #2B6DE8;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

    def setSelected(self, selected):
        if selected:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #EEF7FF;
                    color: #666666;
                    border: none;
                    font-size: 13px;
                    padding: 4px 8px;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #2B6DE8;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #666666;
                    border: none;
                    font-size: 13px;
                    padding: 4px 8px;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #2B6DE8;
                }
            """)

class PDFMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF工具箱")  # 添加窗口标题
        self.setGeometry(100, 100, 800, 500)
        
        # 设置应用图标
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            QWidget {
                background-color: white;
            }
            QLabel {
                color: #333333;
                font-size: 13px;
            }
            QSpinBox {
                color: #333333;
                background-color: white;
                font-size: 13px;
            }
            QListWidget {
                font-size: 13px;
            }
        """)
        
        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建左侧导航栏
        nav_widget = QWidget()
        nav_widget.setStyleSheet("background-color: #F3F4F7;")  # 修改背景色
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)
        nav_widget.setFixedWidth(200)  # 增加导航栏宽度
        
        # 添加Logo或标题
        title_label = QLabel("PDF工具箱")
        title_label.setAlignment(Qt.AlignCenter)  # 文字居中
        title_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 24px;
                font-weight: bold;
                padding: 20px 0px;
                background-color: #F3F4F7;
            }
        """)
        nav_layout.addWidget(title_label)
        
        self.merge_nav = NavButton("PDF合并")
        self.merge_nav.setChecked(True)
        self.merge_nav.clicked.connect(lambda: self.switch_page(0))
        
        self.split_nav = NavButton("PDF提取")
        self.split_nav.clicked.connect(lambda: self.switch_page(1))
        
        nav_layout.addWidget(self.merge_nav)
        nav_layout.addWidget(self.split_nav)
        nav_layout.addStretch()
        nav_widget.setLayout(nav_layout)
        
        # 创建堆叠窗口
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #F3F4F7;")
        
        # 创建PDF合并页面
        merge_page = QWidget()
        merge_layout = QVBoxLayout()
        merge_layout.setContentsMargins(12, 48, 20, 20)
        merge_layout.setSpacing(12)
        
        # 创建列表容器
        list_container = QWidget()
        list_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #F3F4F7;
                border-radius: 4px;
            }
        """)
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(4, 4, 4, 4)
        
        # 文件列表
        self.file_list = DragDropListWidget(self)
        self.file_list.setMinimumHeight(300)
        
        # 添加文件按钮
        self.add_file_button = AddFileButton()
        self.add_file_button.clicked.connect(self.select_files)
        
        list_layout.addWidget(self.file_list)
        list_layout.addWidget(self.add_file_button)
        merge_layout.addWidget(list_container)
        
        # 提示语放在列表下方
        self.merge_label = QLabel("添加要合并的PDF文件，可拖拽调整文件合并顺序")
        self.merge_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
            }
        """)
        merge_layout.addWidget(self.merge_label)
        
        # 底部按钮容器
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(20, 10, 20, 20)
        
        # 按钮靠右放置
        bottom_layout.addStretch()
        self.merge_button = ActionButton("合并PDF")
        self.merge_button.clicked.connect(self.merge_pdfs)
        bottom_layout.addWidget(self.merge_button)
        
        merge_layout.addWidget(bottom_container)
        
        merge_page.setLayout(merge_layout)
        
        # 创建PDF拆分页面
        self.split_page = PDFSplitWidget(self)
        
        # 将页面添加到堆叠窗口
        self.stack.addWidget(merge_page)
        self.stack.addWidget(self.split_page)
        
        # 组装主布局
        main_layout.addWidget(nav_widget)
        main_layout.addWidget(self.stack)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Toast信息标签
        self.toast_label = QLabel("", self)
        self.toast_label.setStyleSheet("""
            QLabel {
                background-color: rgba(240, 240, 240, 0.9);  /* 半透明灰色背景 */
                color: #333333;  /* 深色文字 */
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
            }
        """)
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.setVisible(False)
        self.toast_label.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.toast_label.setAttribute(Qt.WA_TranslucentBackground)
        
        # 存储PDF文件列表
        self.pdf_files = []

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.merge_nav.setChecked(True)
            self.split_nav.setChecked(False)
        else:
            self.merge_nav.setChecked(False)
            self.split_nav.setChecked(True)

    def add_file_with_delete(self, file_path):
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 4, 12, 4)
        
        # 文件名标签
        label = QLabel(os.path.basename(file_path))
        label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 13px;
                border: none;  /* 移除边框 */
                background: transparent;  /* 透明背景 */
            }
        """)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # 删除按钮
        delete_btn = DeleteButton()
        delete_btn.setFixedWidth(40)
        delete_btn.clicked.connect(lambda: self.remove_file(item, file_path))
        
        layout.addWidget(label)
        layout.addWidget(delete_btn)
        
        # 设置整个项目的样式
        widget.setStyleSheet("""
            QWidget {
                background: transparent;  /* 透明背景 */
                border: none;  /* 移除边框 */
            }
        """)
        
        widget.setFixedHeight(36)
        item.setSizeHint(widget.sizeHint())
        
        self.file_list.addItem(item)
        self.file_list.setItemWidget(item, widget)

    def remove_file(self, item, file_path):
        row = self.file_list.row(item)
        self.file_list.takeItem(row)
        if file_path in self.pdf_files:
            self.pdf_files.remove(file_path)
        self.file_list.updateEmptyState()  # 更新空状态

    def handle_dropped_files(self, urls):
        for url in urls:
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
                    if file_path not in self.pdf_files:
                        self.pdf_files.append(file_path)
                        self.add_file_with_delete(file_path)
                elif os.path.isdir(file_path):
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            if file.lower().endswith('.pdf'):
                                full_path = os.path.join(root, file)
                                if full_path not in self.pdf_files:
                                    self.pdf_files.append(full_path)
                                    self.add_file_with_delete(full_path)

    def show_toast(self, message, duration=3000, fade_duration=200):
        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        self.toast_label.move(self.geometry().center() - self.toast_label.rect().center())
        self.toast_label.setVisible(True)
        
        # Start fade out after duration
        QTimer.singleShot(duration, lambda: self.start_fade_out(fade_duration))

    def start_fade_out(self, fade_duration):
        # Fade out animation
        self.animation = QPropertyAnimation(self.toast_label, b"windowOpacity")
        self.animation.setDuration(fade_duration)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(self.hide_toast)
        self.animation.start()

    def hide_toast(self):
        self.toast_label.setVisible(False)
        self.toast_label.setWindowOpacity(1)  # Reset opacity for next use

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择PDF文件", "", "PDF文件 (*.pdf)")
        if files:
            for file in files:
                if file not in self.pdf_files:
                    self.pdf_files.append(file)
                    self.add_file_with_delete(file)  # 使用新的添加方法
            self.show_toast("文件已选择")

    def merge_pdfs(self):
        if not self.pdf_files:
            self.show_toast("未选择任何PDF文件", 3000)
            return
        
        output_file, _ = QFileDialog.getSaveFileName(self, "保存合并后的PDF", "", "PDF文件 (*.pdf)")
        if not output_file:
            return
        
        # Merge the PDF files in the order they appear in the QListWidget
        pdf_writer = PdfWriter()
        
        # 获取每个列表项的实际文件路径
        for index in range(self.file_list.count()):
            item = self.file_list.item(index)
            widget = self.file_list.itemWidget(item)
            file_name = widget.layout().itemAt(0).widget().text()  # 获取文件名标签的文本
            file_path = next((f for f in self.pdf_files if os.path.basename(f) == file_name), None)
            
            if file_path:
                try:
                    pdf_reader = PdfReader(file_path)
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
                except Exception as e:
                    self.show_toast(f"处理文件 {file_name} 时出错")
                    return
        
        try:
            # Write the merged PDF to the output file
            with open(output_file, 'wb') as out:
                pdf_writer.write(out)
            
            self.show_toast("合并完成！文件保存至目标文件夹")
            
            # Clear the list and internal storage
            self.file_list.clear()
            self.pdf_files.clear()
        except Exception as e:
            self.show_toast("保存文件时出错")

def main():
    print("应用程序已启动")
    app = QApplication(sys.argv)
    window = PDFMergerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()