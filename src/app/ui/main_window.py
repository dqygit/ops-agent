from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from app.ui.asset_panel import AssetPanel
from app.ui.chat_panel import ChatPanel
from app.ui.terminal_panel import TerminalPanel


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ops Agent")
        self.resize(1600, 920)

        self.settings_button = QPushButton("Settings")
        self.asset_panel = AssetPanel()
        self.terminal_panel = TerminalPanel()
        self.assistant_panel = ChatPanel()

        self.setObjectName("mainWindow")
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("topBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        title = QLabel("Ops Agent Console")
        title.setObjectName("appTitle")
        subtitle = QLabel("Assets, terminal sessions, and assistant workflows")
        subtitle.setObjectName("appSubtitle")
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addLayout(title_box)
        header_layout.addStretch(1)
        header_layout.addWidget(self.settings_button)
        root_layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.asset_panel)
        splitter.addWidget(self.terminal_panel)
        splitter.addWidget(self.assistant_panel)
        splitter.setSizes([300, 760, 420])
        root_layout.addWidget(splitter, 1)

        self.setStyleSheet(
            """
            QWidget#mainWindow {
                background: #111318;
                color: #e8ecf3;
            }
            QFrame#topBar, QFrame#panelCard {
                background: #171a21;
                border: 1px solid #272c36;
                border-radius: 12px;
            }
            QLabel#appTitle {
                font-size: 20px;
                font-weight: 700;
                color: #f4f7fb;
            }
            QLabel#appSubtitle {
                color: #8d97aa;
                font-size: 12px;
            }
            QLabel#sectionTitle {
                font-size: 14px;
                font-weight: 700;
                color: #f4f7fb;
            }
            QLabel#sectionMeta {
                color: #8d97aa;
                font-size: 12px;
            }
            QPushButton {
                background: #232936;
                border: 1px solid #30384a;
                border-radius: 8px;
                color: #e8ecf3;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background: #2a3140;
            }
            QPushButton:pressed {
                background: #1f2530;
            }
            QPushButton:disabled {
                color: #667085;
                background: #1a1f29;
                border-color: #222834;
            }
            QPushButton#primaryButton {
                background: #2563eb;
                border-color: #2563eb;
                color: white;
                font-weight: 600;
            }
            QPushButton#primaryButton:hover {
                background: #2b6ef3;
            }
            QPushButton#dangerButton {
                background: #3a1f28;
                border-color: #6b2a3d;
                color: #ffc9d2;
            }
            QPushButton#tabButton[active='true'] {
                background: #1f4db8;
                border-color: #2d63de;
                color: white;
                font-weight: 600;
            }
            QListWidget, QPlainTextEdit, QLineEdit, QComboBox {
                background: #0f1218;
                border: 1px solid #272c36;
                border-radius: 10px;
                color: #e8ecf3;
                selection-background-color: #2457d6;
                selection-color: white;
            }
            QListWidget, QPlainTextEdit {
                padding: 8px;
            }
            QLineEdit, QComboBox {
                padding: 8px 10px;
            }
            QComboBox QAbstractItemView {
                background: #0f1218;
                color: #e8ecf3;
                border: 1px solid #272c36;
                selection-background-color: #2457d6;
            }
            QSplitter::handle {
                background: #111318;
                width: 6px;
            }
            QScrollBar:vertical {
                background: #111318;
                width: 10px;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30384a;
                min-height: 24px;
                border-radius: 5px;
            }
            """
        )
