import sys
import threading
import time
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QLabel, QSpinBox, 
                             QGroupBox, QGridLayout, QMessageBox, QComboBox,
                             QDoubleSpinBox, QTabWidget, QScrollArea)  # 添加 QTabWidget 和 QScrollArea
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTime
from pynput.keyboard import Controller, Key
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor


class TypeThread(QThread):
    """用于后台输入文本的线程"""
    update_status = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, text, delay_before_start, char_delay, method, repeat_times):
        super().__init__()
        self.text = text
        self.delay_before_start = delay_before_start
        self.char_delay = char_delay
        self.method = method
        self.repeat_times = repeat_times
        self.is_running = True
        self.keyboard = Controller()
    
    def run(self):
        try:
            self.update_status.emit(f"等待 {self.delay_before_start} 秒后开始输入...")
            
            # 倒计时
            for i in range(self.delay_before_start, 0, -1):
                if not self.is_running:
                    return
                self.update_status.emit(f"{i} 秒后开始输入...")
                time.sleep(1)
            
            total_chars = len(self.text) * self.repeat_times
            chars_typed = 0
            
            for repeat in range(self.repeat_times):
                if not self.is_running:
                    return
                    
                if self.repeat_times > 1:
                    self.update_status.emit(f"开始第 {repeat + 1}/{self.repeat_times} 轮输入...")
                
                for i, char in enumerate(self.text):
                    if not self.is_running:
                        return
                    
                    # 计算进度
                    chars_typed += 1
                    progress = int((chars_typed / total_chars) * 100)
                    self.update_progress.emit(progress)
                    
                    # 输入字符
                    if self.method == "逐个字符":
                        self.type_character(char)
                    elif self.method == "模拟按键":
                        self.type_with_controller(char)
                    
                    # 更新状态
                    if i < len(self.text) - 1 or repeat < self.repeat_times - 1:
                        self.update_status.emit(f"已输入: '{char}' (进度: {chars_typed}/{total_chars})")
                    
                    # 字符间延迟
                    if self.char_delay > 0 and (i < len(self.text) - 1 or repeat < self.repeat_times - 1):
                        time.sleep(self.char_delay)
                
                # 重复之间的延迟（除了最后一次）
                if repeat < self.repeat_times - 1:
                    time.sleep(0.5)
            
            self.update_status.emit(f"输入完成！共输入了 {total_chars} 个字符")
            self.update_progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            self.update_status.emit(f"错误: {str(e)}")
    
    def type_character(self, char):
        """逐个字符输入"""
        special_keys = {
            '\n': Key.enter,
            '\t': Key.tab,
            ' ': Key.space,
        }
        
        if char in special_keys:
            self.keyboard.press(special_keys[char])
            self.keyboard.release(special_keys[char])
        else:
            self.keyboard.type(char)
    
    def type_with_controller(self, char):
        """使用pynput的Controller输入"""
        self.keyboard.type(char)
    
    def stop(self):
        self.is_running = False


class AutoTyperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.type_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Typer')
        self.setGeometry(200, 200, 700, 600)
        
        # 设置窗口图标
        self.setWindowIcon(self.create_icon())
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 创建选项卡控件
        tab_widget = QTabWidget()
        
        # 主功能页面
        main_page = QWidget()
        main_page_layout = QVBoxLayout()
        
        # 文本输入区域
        text_group = QGroupBox("输入文本")
        text_layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在这里输入要自动输入的文本（支持中文和英文）...")
        self.text_edit.setMinimumHeight(150)
        text_layout.addWidget(self.text_edit)
        
        # 示例文本按钮
        example_btn = QPushButton("插入示例文本")
        example_btn.clicked.connect(self.insert_example_text)
        example_btn.setStyleSheet("background-color: #ecf0f1; padding: 5px;")
        text_layout.addWidget(example_btn)
        
        text_group.setLayout(text_layout)
        main_page_layout.addWidget(text_group)
        
        # 设置区域
        settings_group = QGroupBox("设置")
        settings_layout = QGridLayout()
        
        # 开始前延迟
        settings_layout.addWidget(QLabel("开始前延迟(秒):"), 0, 0)
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 60)
        self.delay_spinbox.setValue(3)
        self.delay_spinbox.setSuffix(" 秒")
        settings_layout.addWidget(self.delay_spinbox, 0, 1)
        
        # 字符间延迟 - 使用 QDoubleSpinBox
        settings_layout.addWidget(QLabel("字符间延迟(秒):"), 1, 0)
        self.char_delay_spinbox = QDoubleSpinBox()  # 改为 QDoubleSpinBox
        self.char_delay_spinbox.setRange(0, 5)
        self.char_delay_spinbox.setValue(0)
        self.char_delay_spinbox.setSingleStep(0.1)  # 现在可以设置小数步长
        self.char_delay_spinbox.setDecimals(2)  # 设置小数点后2位
        self.char_delay_spinbox.setSuffix(" 秒")
        settings_layout.addWidget(self.char_delay_spinbox, 1, 1)
        
        # 输入方法
        settings_layout.addWidget(QLabel("输入方法:"), 2, 0)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["模拟按键", "逐个字符"])  # 默认改为模拟按键
        self.method_combo.setCurrentIndex(0)  # 设置默认选中模拟按键
        self.method_combo.setToolTip("模拟按键: 更快更简洁\n逐个字符: 更慢但更可靠")
        settings_layout.addWidget(self.method_combo, 2, 1)
        
        # 重复次数
        settings_layout.addWidget(QLabel("重复次数:"), 3, 0)
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setRange(1, 100)
        self.repeat_spinbox.setValue(1)
        settings_layout.addWidget(self.repeat_spinbox, 3, 1)
        
        settings_group.setLayout(settings_layout)
        main_page_layout.addWidget(settings_group)
        
        # 状态显示
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f8f9fa; border: 1px solid #dee2e6;")
        self.status_label.setMinimumHeight(30)
        status_layout.addWidget(self.status_label)
        
        # 进度条区域
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        
        self.progress_label = QLabel("0%")
        self.progress_label.setFixedWidth(40)
        progress_layout.addWidget(self.progress_label)
        
        status_layout.addLayout(progress_layout)
        
        status_group.setLayout(status_layout)
        main_page_layout.addWidget(status_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始自动输入")
        self.start_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 10px;")
        self.start_btn.clicked.connect(self.start_typing)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 10px;")
        self.stop_btn.clicked.connect(self.stop_typing)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 10px;")
        self.clear_btn.clicked.connect(self.clear_text)
        button_layout.addWidget(self.clear_btn)
        
        main_page_layout.addLayout(button_layout)
        
        # 使用说明
        instructions = QLabel("使用方法: 1. 输入文本 2. 设置参数 3. 点击开始 4. 在3秒内切换到目标窗口")
        instructions.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 5px;")
        instructions.setWordWrap(True)
        main_page_layout.addWidget(instructions)
        
        main_page.setLayout(main_page_layout)
        
        # 帮助页面
        help_page = QWidget()
        help_page_layout = QVBoxLayout()
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        help_content = QWidget()
        help_content_layout = QVBoxLayout()
        
        # 应用基本用法
        app_usage_group = QGroupBox("应用基本用法")
        app_usage_layout = QVBoxLayout()
        
        app_usage_text = QTextEdit()
        app_usage_text.setReadOnly(True)
        app_usage_text.setStyleSheet("background-color: transparent; border: none;")
        app_usage_text.setPlainText("""Typer 自动输入工具使用指南

一、基本功能
Typer 是一款基于 PyQt5 和 pynput 开发的自动文本输入工具，可以模拟键盘输入，帮助用户自动输入文本内容。

二、使用步骤
1. 在"输入文本"区域输入要自动输入的内容
2. 设置相关参数：
   - 开始前延迟：点击开始后等待的秒数，用于切换到目标窗口
   - 字符间延迟：每个字符输入之间的间隔时间
   - 输入方法：选择模拟按键或逐个字符模式
   - 重复次数：文本重复输入的次数
3. 点击"开始自动输入"按钮
4. 在倒计时结束前切换到目标窗口（如Word、浏览器等）
5. 程序将自动输入文本

三、快捷功能
- 插入示例文本：点击按钮可快速插入中英文示例文本
- 清空：一键清空输入区域
- 停止：在输入过程中可随时停止

四、注意事项
- 请确保在倒计时结束前切换到目标窗口
- 输入过程中请勿移动鼠标或切换窗口，以免影响输入
- 如果输入失败，请尝试增加字符间延迟

五、快捷键（暂无）
目前版本暂未提供快捷键功能

六、常见问题
Q: 输入不生效怎么办？
A: 请确保在倒计时结束前切换到正确的窗口，或尝试增加字符间延迟

Q: 中文输入有问题？
A: 中文输入需要确保系统输入法处于中文状态

Q: 特殊字符无法输入？
A: 请尝试使用"逐个字符"输入方法
""")
        app_usage_layout.addWidget(app_usage_text)
        app_usage_group.setLayout(app_usage_layout)
        help_content_layout.addWidget(app_usage_group)
        
        # 文档内容介绍
        doc_content_group = QGroupBox("输入方法说明文档")
        doc_content_layout = QVBoxLayout()
        
        doc_content_text = QTextEdit()
        doc_content_text.setReadOnly(True)
        doc_content_text.setStyleSheet("background-color: transparent; border: none;")
        doc_content_text.setPlainText("""模拟按键和逐个字符的区别详解

一、核心区别
这两种方法的区别主要在于处理特殊字符和输入方式的不同：

1. 逐个字符方法 (type_character)
特点：
- 能正确处理特殊按键（回车、Tab、空格等）
- 兼容性更好
- 但可能稍慢一些
- 特别适合需要精确控制按键的场景

2. 模拟按键方法 (type_with_controller)
特点：
- 所有字符统一用type()方法
- 代码更简洁
- 但可能无法正确处理某些特殊字符
- 在某些应用中，回车、Tab等可能不被识别

二、实际对比示例
假设输入"Hello World!\n测试中文"

逐个字符方法处理：
- "H" → keyboard.type('H')
- "e" → keyboard.type('e')
- "l" → keyboard.type('l')
- "l" → keyboard.type('l')
- "o" → keyboard.type('o')
- "," → keyboard.type(',')
- " " → keyboard.press(Key.space) + keyboard.release(Key.space)
- "W" → keyboard.type('W')
- "o" → keyboard.type('o')
- "r" → keyboard.type('r')
- "l" → keyboard.type('l')
- "d" → keyboard.type('d')
- "!" → keyboard.type('!')
- "\\n" → keyboard.press(Key.enter) + keyboard.release(Key.enter)
- "测" → keyboard.type('测')
- "试" → keyboard.type('试')
- "中" → keyboard.type('中')
- "文" → keyboard.type('文')

模拟按键方法处理：
- 所有字符 → keyboard.type(字符)
- 包括回车、Tab、空格也都是直接用type()

三、为什么有这两种方法？
1. 兼容性问题：
   - 某些应用程序对按键事件的处理方式不同
   - 有些应用只识别真正的按键事件（press/release）

2. 性能考虑：
   - 逐个字符方法在特殊字符处理上更精确
   - 模拟按键方法代码更简洁，执行更一致

四、实际应用场景建议

使用"逐个字符"方法的场景：
- 在终端/命令行中输入
- 在游戏或全屏应用中输入
- 需要输入Tab键进行缩进的代码编辑器
- 需要使用方向键、功能键的复杂操作
- 在虚拟机、远程桌面中输入

使用"模拟按键"方法的场景：
- 在Word、记事本等文本编辑器中输入普通文本
- 在浏览器表单中填写信息
- 输入简单的英文/中文文本
- 大多数普通应用程序

五、测试建议
如果不确定用哪种方法，可以：
1. 先用"模拟按键"方法测试
2. 如果遇到问题（回车、Tab等无效），切换到"逐个字符"方法
3. 如果两种都不行，可以调整字符间延迟（尝试0.1-0.5秒）

六、type、press和release三者的关系
- type() 是高级方法，一次性完成按下和释放
- press() 和 release() 是低级方法，需要成对使用
- type() 内部实际上调用了 press() 和 release()

总结：如果不确定用哪种，或者需要处理特殊按键，建议使用"逐个字符"方法。如果只是简单文本输入，可以用"模拟按键"以获取更快的速度。
""")
        doc_content_layout.addWidget(doc_content_text)
        doc_content_group.setLayout(doc_content_layout)
        help_content_layout.addWidget(doc_content_group)
        
        help_content.setLayout(help_content_layout)
        scroll_area.setWidget(help_content)
        help_page_layout.addWidget(scroll_area)
        help_page.setLayout(help_page_layout)
        
        # 添加选项卡
        tab_widget.addTab(main_page, "主功能")
        tab_widget.addTab(help_page, "帮助")
        
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)
        
    def insert_example_text(self):
        example_text = """你好，这是一个Typer的示例。
Hello, this is an example of auto typer.
您可以输入任何中文或英文文本。
You can type any Chinese or English text.
程序将在倒计时后自动输入这些内容。
The program will automatically type this content after the countdown."""
        self.text_edit.setPlainText(example_text)
    
    def start_typing(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要自动输入的文本！")
            return
        
        delay = self.delay_spinbox.value()
        char_delay = self.char_delay_spinbox.value()  # 现在直接获取浮点数值
        method = self.method_combo.currentText()
        repeat = self.repeat_spinbox.value()
        
        # 显示提示信息
        reply = QMessageBox.question(
            self, "准备开始",
            f"将在 {delay} 秒后开始输入文本。\n\n"
            f"字符数: {len(text)} × {repeat} = {len(text) * repeat}\n"
            f"总输入时间约: {len(text) * repeat * char_delay + delay:.1f} 秒\n\n"
            f"请切换到目标窗口准备接收输入！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.No:
            return
        
        # 创建并启动输入线程
        self.type_thread = TypeThread(text, delay, char_delay, method, repeat)
        self.type_thread.update_status.connect(self.update_status)
        self.type_thread.update_progress.connect(self.update_progress)
        self.type_thread.finished.connect(self.typing_finished)
        
        # 更新按钮状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.text_edit.setEnabled(False)
        self.delay_spinbox.setEnabled(False)
        self.char_delay_spinbox.setEnabled(False)
        self.method_combo.setEnabled(False)
        self.repeat_spinbox.setEnabled(False)
        
        # 启动线程
        self.type_thread.start()
    
    def stop_typing(self):
        if self.type_thread and self.type_thread.isRunning():
            self.type_thread.stop()
            self.type_thread.wait()
            self.update_status("输入已停止")
            self.typing_finished()
    
    def typing_finished(self):
        # 恢复按钮状态
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.text_edit.setEnabled(True)
        self.delay_spinbox.setEnabled(True)
        self.char_delay_spinbox.setEnabled(True)
        self.method_combo.setEnabled(True)
        self.repeat_spinbox.setEnabled(True)
        
        # 清空线程引用
        self.type_thread = None
    
    def update_status(self, message):
        current_time = QTime.currentTime().toString("hh:mm:ss")
        self.status_label.setText(f"[{current_time}] {message}")
    
    def update_progress(self, progress):
        self.progress_label.setText(f"{progress}%")
    
    def clear_text(self):
        self.text_edit.clear()
        self.status_label.setText("已清空文本")
        self.progress_label.setText("0%")
    
    def closeEvent(self, event):
        # 确保在关闭窗口时停止线程
        if self.type_thread and self.type_thread.isRunning():
            self.type_thread.stop()
            self.type_thread.wait()
        event.accept()
    
    def create_icon(self):
        """创建窗口图标，优先读取icon.ico，否则生成默认图标"""
        # 检查当前目录下是否存在icon.ico
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        
        # 如果不存在，生成一个默认图标（键盘样式）
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制键盘背景
        keyboard_color = QColor(70, 130, 180)
        painter.setBrush(keyboard_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 4, 4)
        
        # 绘制按键
        key_color = QColor(255, 255, 255)
        painter.setBrush(key_color)
        
        # 绘制三行按键
        # 第一行
        painter.drawRoundedRect(4, 4, 6, 6, 1, 1)
        painter.drawRoundedRect(11, 4, 6, 6, 1, 1)
        painter.drawRoundedRect(18, 4, 6, 6, 1, 1)
        
        # 第二行
        painter.drawRoundedRect(4, 12, 6, 6, 1, 1)
        painter.drawRoundedRect(11, 12, 8, 6, 1, 1)
        painter.drawRoundedRect(21, 12, 6, 6, 1, 1)
        
        # 第三行
        painter.drawRoundedRect(4, 20, 8, 6, 1, 1)
        painter.drawRoundedRect(14, 20, 10, 6, 1, 1)
        
        # 绘制键盘符号
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(QFont("Arial", 4))
        painter.drawText(5, 8, "Q")
        painter.drawText(12, 8, "W")
        painter.drawText(19, 8, "E")
        painter.drawText(5, 16, "A")
        painter.drawText(13, 16, "S")
        painter.drawText(22, 16, "D")
        painter.drawText(6, 24, "Shift")
        
        painter.end()
        
        return QIcon(pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion风格，使应用在不同平台上看起来一致
    
    # 设置应用样式
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 2px solid #bdc3c7;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QSpinBox, QComboBox, QTextEdit, QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #bdc3c7;
            border-radius: 3px;
        }
    """)
    
    window = AutoTyperApp()
    window.show()
    sys.exit(app.exec_())