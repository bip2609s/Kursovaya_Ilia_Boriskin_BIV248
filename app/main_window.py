from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QLineEdit,
    QLabel,
    QPushButton,
    QListWidget,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QHBoxLayout,
    QListWidgetItem,
)
from PySide6.QtCore import Qt

from app.repo_worker import RepoWorker
from app.clone_worker import CloneWorker
from app.repo_list_item import RepoListItem


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Repo Downloader")
        self.setGeometry(100, 100, 800, 600)
        self.token = None
        self.repos = []
        self.selected_repos = []
        self.setup_ui()
        self.load_stylesheet()
        self.clone_workers = []

    def load_stylesheet(self):
        try:
            with open("./style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Не удалось загрузить стиль: {e}")

    def setup_ui(self):
        self.layout = QVBoxLayout(self)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Search by Language", "Search by User"])
        self.layout.addWidget(self.mode_combo)

        self.param_layout = QVBoxLayout()

        self.language_input = QLineEdit(placeholderText="Language (e.g. Python)")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["stars", "forks", "updated"])
        self.order_combo = QComboBox()
        self.order_combo.addItems(["desc", "asc"])
        self.per_page_input = QLineEdit("100")
        self.username_input = QLineEdit(placeholderText="GitHub username")
        self.token_input = QLineEdit(placeholderText="GitHub token (optional)")
        self.token_input.setEchoMode(QLineEdit.Password)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.start_search)

        self.result_list = QListWidget()
        self.result_list.itemChanged.connect(self.update_selection)

        self.clone_btn = QPushButton("Clone Selected")
        self.clone_btn.setEnabled(False)
        self.clone_btn.clicked.connect(self.start_cloning)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.layout.addLayout(self.param_layout)
        self.layout.addWidget(self.token_input)
        self.layout.addWidget(self.search_btn)
        self.layout.addWidget(self.result_list)
        self.layout.addWidget(self.clone_btn)
        self.layout.addWidget(self.progress_bar)

        self.mode_combo.currentIndexChanged.connect(self.update_params_ui)
        self.update_params_ui()

    def update_params_ui(self):
        for i in reversed(range(self.param_layout.count())):
            self.param_layout.itemAt(i).widget().setParent(None)
        if self.mode_combo.currentIndex() == 0:
            self.param_layout.addWidget(QLabel("Language:"))
            self.param_layout.addWidget(self.language_input)
            self.param_layout.addWidget(QLabel("Sort by:"))
            self.param_layout.addWidget(self.sort_combo)
            self.param_layout.addWidget(QLabel("Order:"))
            self.param_layout.addWidget(self.order_combo)
            self.param_layout.addWidget(QLabel("Results per page:"))
            self.param_layout.addWidget(self.per_page_input)
        else:
            self.param_layout.addWidget(QLabel("Username:"))
            self.param_layout.addWidget(self.username_input)

    def start_search(self):
        self.token = self.token_input.text() or None
        self.result_list.clear()
        if self.mode_combo.currentIndex() == 0:
            params = {
                "language": self.language_input.text() or "Verilog",
                "sort_by": self.sort_combo.currentText(),
                "order": self.order_combo.currentText(),
                "token": self.token,
            }
            self.worker = RepoWorker("language", **params)
        else:
            params = {"username": self.username_input.text(), "token": self.token}
            self.worker = RepoWorker("user", **params)
        self.worker.finished.connect(self.display_repos)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def display_repos(self, repos):
        self.repos = repos
        self.result_list.clear()
        for repo in repos:
            item_widget = RepoListItem(repo)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.result_list.addItem(list_item)
            self.result_list.setItemWidget(list_item, item_widget)
        self.clone_btn.setEnabled(True)

    def update_selection(self):
        self.selected_repos = []
        for i in range(self.result_list.count()):
            list_item = self.result_list.item(i)
            item_widget = self.result_list.itemWidget(list_item)
            if item_widget.isChecked():
                repo_info = item_widget.repo_info
                repo_info["branch"] = item_widget.getSelectedBranch()
                self.selected_repos.append(repo_info)

    def start_cloning(self):
        self.selected_repos = []
        for i in range(self.result_list.count()):
            list_item = self.result_list.item(i)
            item_widget = self.result_list.itemWidget(list_item)
            if item_widget.isChecked():
                repo_info = item_widget.repo_info
                repo_info["branch"] = item_widget.getSelectedBranch()
                self.selected_repos.append(repo_info)
        if not self.selected_repos:
            QMessageBox.warning(self, "Ошибка", "Выберите репозитории!")
            return
        self.clone_dir = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not self.clone_dir:
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.selected_repos))
        self.progress_bar.setValue(0)
        self.clone_workers = []
        for repo in self.selected_repos:
            worker = CloneWorker(repo["url"], repo["branch"], self.clone_dir)
            worker.finished.connect(self.update_progress)
            worker.finished.connect(self.handle_clone_finished)
            worker.error.connect(self.show_error)
            self.clone_workers.append(worker)
            worker.start()

    def update_progress(self):
        current = self.progress_bar.value()
        self.progress_bar.setValue(current + 1)

    def handle_clone_finished(self):
        if all(not worker.isRunning() for worker in self.clone_workers):
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "Complete", "Cloning finished!")

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)
