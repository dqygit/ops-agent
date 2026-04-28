from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QTabWidget, QVBoxLayout, QWidget

from app.services.asset_service import (
    create_asset_record,
    delete_asset_record,
    get_asset_record,
    list_asset_records,
    update_asset_record,
)


class AssetPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.asset_list = QListWidget()
        self.history_list = QListWidget()
        self.add_asset_button = QPushButton("Add Asset")
        self.edit_asset_button = QPushButton("Edit Asset")
        self.delete_asset_button = QPushButton("Delete Asset")
        self._session_factory = None
        self._asset_editor = None
        self._history_loader = None
        self._selection_listeners = []
        self._history_selection_listeners = []
        tabs = QTabWidget()
        tabs.addTab(self.asset_list, "Assets")
        tabs.addTab(self.history_list, "History")
        actions = QHBoxLayout()
        actions.addWidget(self.add_asset_button)
        actions.addWidget(self.edit_asset_button)
        actions.addWidget(self.delete_asset_button)
        layout = QVBoxLayout(self)
        layout.addLayout(actions)
        layout.addWidget(tabs)
        self.add_asset_button.clicked.connect(self._handle_add_clicked)
        self.edit_asset_button.clicked.connect(self._handle_edit_clicked)
        self.delete_asset_button.clicked.connect(self.delete_selected_asset)
        self.asset_list.currentItemChanged.connect(self._handle_current_item_changed)
        self.history_list.itemClicked.connect(self._handle_history_item_clicked)

    def bind_asset_store(self, session_factory) -> None:
        self._session_factory = session_factory
        self.refresh_assets()

    def bind_asset_editor(self, asset_editor) -> None:
        self._asset_editor = asset_editor

    def bind_selection_listener(self, selection_listener) -> None:
        self._selection_listeners.append(selection_listener)
        self._notify_selection_listener()

    def bind_history_loader(self, history_loader) -> None:
        self._history_loader = history_loader
        self.refresh_history()

    def bind_history_selection_listener(self, selection_listener) -> None:
        self._history_selection_listeners.append(selection_listener)

    def refresh_assets(self, selected_asset_id=None) -> None:
        self.asset_list.clear()
        if self._session_factory is None:
            self.refresh_history(None)
            return
        with self._session_factory() as session:
            for asset in list_asset_records(session):
                item = QListWidgetItem(f"{asset.name} ({asset.asset_type}) @ {asset.host}:{asset.port}")
                item.setData(Qt.ItemDataRole.UserRole, asset.id)
                self.asset_list.addItem(item)
                if selected_asset_id is not None and asset.id == selected_asset_id:
                    self.asset_list.setCurrentItem(item)

    def refresh_history(self, asset=None) -> None:
        self.history_list.clear()
        if self._history_loader is None or asset is None:
            return
        for assistant_session in self._history_loader(asset):
            item = QListWidgetItem(assistant_session.title)
            item.setData(Qt.ItemDataRole.UserRole, assistant_session.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, assistant_session.active_model)
            self.history_list.addItem(item)

    def create_asset(self, asset_data):
        if self._session_factory is None:
            return None
        with self._session_factory() as session:
            asset = create_asset_record(session, asset_data)
        self.refresh_assets(asset.id)
        return asset

    def update_selected_asset(self, asset_data):
        if self._session_factory is None:
            return None
        item = self.asset_list.currentItem()
        if item is None:
            return None
        asset_id = item.data(Qt.ItemDataRole.UserRole)
        with self._session_factory() as session:
            asset = update_asset_record(session, asset_id, asset_data)
        self.refresh_assets(asset_id)
        return asset

    def delete_selected_asset(self) -> bool:
        if self._session_factory is None:
            return False
        item = self.asset_list.currentItem()
        if item is None:
            return False
        asset_id = item.data(Qt.ItemDataRole.UserRole)
        with self._session_factory() as session:
            deleted = delete_asset_record(session, asset_id)
        self.refresh_assets()
        return deleted

    def _handle_add_clicked(self) -> None:
        if self._asset_editor is None:
            return
        asset_data = self._asset_editor(None)
        if asset_data is not None:
            self.create_asset(asset_data)

    def _handle_edit_clicked(self) -> None:
        if self._asset_editor is None:
            return
        item = self.asset_list.currentItem()
        if item is None:
            return
        asset_data = self._asset_editor(item.data(Qt.ItemDataRole.UserRole))
        if asset_data is not None:
            self.update_selected_asset(asset_data)

    def _handle_current_item_changed(self, _current, _previous) -> None:
        self._notify_selection_listener()

    def _handle_history_item_clicked(self, item) -> None:
        session_id = item.data(Qt.ItemDataRole.UserRole)
        model_name = item.data(Qt.ItemDataRole.UserRole + 1)
        for selection_listener in self._history_selection_listeners:
            selection_listener(session_id, model_name)

    def _notify_selection_listener(self) -> None:
        if self._session_factory is None:
            self.refresh_history(None)
            for selection_listener in self._selection_listeners:
                selection_listener(None)
            return
        item = self.asset_list.currentItem()
        if item is None:
            self.refresh_history(None)
            for selection_listener in self._selection_listeners:
                selection_listener(None)
            return
        asset_id = item.data(Qt.ItemDataRole.UserRole)
        with self._session_factory() as session:
            asset = get_asset_record(session, asset_id)
        self.refresh_history(asset)
        for selection_listener in self._selection_listeners:
            selection_listener(asset)
