from PySide6.QtWidgets import QWidget, QCheckBox, QComboBox, QHBoxLayout
from PySide6.QtCore import Signal, Qt


class RepoListItem(QWidget):
    stateChanged = Signal()

    def __init__(self, repo_info):
        super().__init__()
        self.repo_info = repo_info
        self.checkbox = QCheckBox()
        self.checkbox.setText(
            f"{repo_info['name']} by {repo_info['owner']} (★{repo_info['stars']})"
        )
        self.branch_combo = QComboBox()
        self.checkbox.setChecked(repo_info.get("selected", False))
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        self.branch_combo.addItems(repo_info.get("branches", ["main"]))
        layout = QHBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.branch_combo)
        layout.addStretch()
        self.setLayout(layout)

        self.checkbox.stateChanged.connect(self.on_checkbox_changed)

    def on_checkbox_changed(self, state):
        self.repo_info["selected"] = (state == Qt.Checked)
        self.stateChanged.emit()

    def isChecked(self):
        return self.checkbox.isChecked()

    def setChecked(self, checked):
        self.checkbox.setChecked(checked)
        self.repo_info["selected"] = checked

    def getSelectedBranch(self):
        return self.branch_combo.currentText()
