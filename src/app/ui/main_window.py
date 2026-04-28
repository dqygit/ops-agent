from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from app.ui.asset_panel import AssetPanel
from app.ui.chat_panel import ChatPanel
from app.ui.terminal_panel import TerminalPanel


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ops Agent")
        self.resize(1440, 900)
        self.settings_button = QPushButton("Settings")
        self.asset_panel = AssetPanel()
        self.terminal_panel = TerminalPanel()
        self.assistant_panel = ChatPanel()
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self.settings_button)
        layout = QHBoxLayout()
        layout.addWidget(self.asset_panel, 2)
        layout.addWidget(self.terminal_panel, 4)
        layout.addWidget(self.assistant_panel, 3)
        root_layout.addLayout(layout)
