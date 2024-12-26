import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QListWidget, QProgressBar, QLabel
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation
from PyPDF2 import PdfReader, PdfWriter

class PDFMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF工具箱")
        self.setGeometry(100, 100, 400, 300)
        
        # Set up the layout
        layout = QVBoxLayout()
        
        # Label for instructions
        self.label = QLabel("选择PDF文件进行合并（支持拖拽调整顺序）：")
        layout.addWidget(self.label)
        
        # List widget to display selected files
        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self.file_list)
        
        # Button to select PDF files
        self.select_button = QPushButton("选择PDF文件", self)
        self.select_button.clicked.connect(self.select_files)
        layout.addWidget(self.select_button)
        
        # Button to merge PDF files
        self.merge_button = QPushButton("合并PDF", self)
        self.merge_button.clicked.connect(self.merge_pdfs)
        layout.addWidget(self.merge_button)
        
        # Progress bar
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)
        
        # Toast message label
        self.toast_label = QLabel("", self)
        self.toast_label.setStyleSheet("background-color: black; color: white; padding: 5px; border-radius: 5px;")
        self.toast_label.setAlignment(Qt.AlignCenter)
        self.toast_label.setVisible(False)
        self.toast_label.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.toast_label.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set the central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        # List to store selected files
        self.pdf_files = []

    def show_toast(self, message, duration=3000, fade_duration=500):
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

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().endswith('.pdf'):
                file_path = url.toLocalFile()
                if file_path not in self.pdf_files:
                    self.pdf_files.append(file_path)
                    self.file_list.addItem(os.path.basename(file_path))
        self.show_toast("文件已添加")

    def select_files(self):
        # Open file dialog to select PDF files
        files, _ = QFileDialog.getOpenFileNames(self, "选择PDF文件", "", "PDF文件 (*.pdf)")
        if files:
            for file in files:
                if file not in self.pdf_files:
                    self.pdf_files.append(file)
                    self.file_list.addItem(os.path.basename(file))
            self.show_toast("文件已选择")

    def merge_pdfs(self):
        if not self.pdf_files:
            self.show_toast("未选择任何PDF文件。", 3000)
            return
        
        # Open file dialog to save the merged PDF
        output_file, _ = QFileDialog.getSaveFileName(self, "保存合并后的PDF", "", "PDF文件 (*.pdf)")
        if not output_file:
            return
        
        # Merge the PDF files in the order they appear in the QListWidget
        pdf_writer = PdfWriter()
        total_pages = 0
        for index in range(self.file_list.count()):
            file_name = self.file_list.item(index).text()
            file_path = next((f for f in self.pdf_files if os.path.basename(f) == file_name), None)
            if file_path:
                pdf_reader = PdfReader(file_path)
                total_pages += len(pdf_reader.pages)
        
        current_page = 0
        for index in range(self.file_list.count()):
            file_name = self.file_list.item(index).text()
            file_path = next((f for f in self.pdf_files if os.path.basename(f) == file_name), None)
            if file_path:
                pdf_reader = PdfReader(file_path)
                for page in range(len(pdf_reader.pages)):
                    pdf_writer.add_page(pdf_reader.pages[page])
                    current_page += 1
                    self.progress_bar.setValue(int((current_page / total_pages) * 100))
        
        # Write the merged PDF to the output file
        with open(output_file, 'wb') as out:
            pdf_writer.write(out)
        
        self.show_toast("合并成功！")
        self.progress_bar.setValue(0)  # Reset progress bar
        
        # Clear the list and internal storage
        self.file_list.clear()
        self.pdf_files.clear()

def main():
    print("应用程序已启动")  # Debugging line to ensure main() is called
    app = QApplication(sys.argv)
    window = PDFMergerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()