from PySide6.QtWidgets import QWidget, QCheckBox, QComboBox, QHBoxLayout


class RepoListItem(QWidget):
    def __init__(self, repo_info):
        super().__init__()
        self.repo_info = repo_info
        self.checkbox = QCheckBox()
        self.checkbox.setText(
            f"{repo_info['name']} by {repo_info['owner']} (★{repo_info['stars']})"
        )
        self.branch_combo = QComboBox()
        self.branch_combo.addItems(repo_info.get("branches", ["main"]))
        layout = QHBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.branch_combo)
        layout.addStretch()
        self.setLayout(layout)

    def isChecked(self):
        return self.checkbox.isChecked()

    def getSelectedBranch(self):
        return self.branch_combo.currentText()
