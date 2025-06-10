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
    QMainWindow,
)
from PySide6.QtCore import Qt

from app.repo_worker import RepoWorker
from app.clone_worker import CloneWorker
from app.repo_list_item import RepoListItem


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Repo Downloader")
        self.setGeometry(100, 100, 800, 600)
        self.token = None
        self.repos_all = []  # Все загруженные репозитории
        self.current_page = 1  # Текущая страница
        self.per_page = 100  # Репозиториев на страницу
        self.selected_repos = []
        self.setup_ui()
        self.load_stylesheet()
        self.clone_workers = []
        self.repo_worker = None

    def load_stylesheet(self):
        try:
            with open("./style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Не удалось загрузить стиль: {e}")

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()

        # Выбор режима поиска
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Search by Language", "Search by User"])
        self.layout.addWidget(self.mode_combo)

        # Параметры поиска
        self.param_layout = QVBoxLayout()
        self.language_input = QLineEdit(placeholderText="Language (e.g. Python)")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["stars", "forks", "updated"])
        self.order_combo = QComboBox()
        self.order_combo.addItems(["desc", "asc"])
        self.per_page_input = QLineEdit("100")  # По умолчанию 100
        self.username_input = QLineEdit(placeholderText="GitHub username")

        # Токен
        self.token_input = QLineEdit(placeholderText="GitHub token (optional)")
        self.token_input.setEchoMode(QLineEdit.Password)

        # Кнопка поиска
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.start_search)

        # Навигация
        self.prev_btn = QPushButton("Назад")
        self.next_btn = QPushButton("Вперёд")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)

        # Страница и список
        self.page_label = QLabel()
        self.result_list = QListWidget()
        self.result_list.itemChanged.connect(self.update_selection)

        # Клонирование
        self.clone_btn = QPushButton("Clone Selected")
        self.clone_btn.setEnabled(False)
        self.clone_btn.clicked.connect(self.start_cloning)

        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # Добавляем всё на форму
        self.layout.addLayout(self.param_layout)
        self.layout.addWidget(self.token_input)
        self.layout.addWidget(self.search_btn)
        self.layout.addWidget(self.prev_btn)
        self.layout.addWidget(self.next_btn)
        self.layout.addWidget(self.page_label)
        self.layout.addWidget(self.result_list)
        self.layout.addWidget(self.clone_btn)
        self.layout.addWidget(self.progress_bar)
        self.central_widget.setLayout(self.layout)

        # Обновление интерфейса
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
        if self.repo_worker and self.repo_worker.isRunning():
            return  # Блокируем повторный запуск

        self.token = self.token_input.text() or None
        self.result_list.clear()
        self.current_page = 1

        self.search_btn.setText("Поиск...")
        self.search_btn.setEnabled(False)

        if self.mode_combo.currentIndex() == 0:
            params = {
                "language": self.language_input.text() or "Verilog",
                "sort_by": self.sort_combo.currentText(),
                "order": self.order_combo.currentText(),
                "token": self.token,
            }
            self.repo_worker = RepoWorker("language", **params)
        else:
            params = {"username": self.username_input.text(), "token": self.token}
            self.repo_worker = RepoWorker("user", **params)

        def on_finished(repos):
            self.repos_all = repos
            self.display_current_page()
            self.repo_worker = None
            self.search_btn.setText("Search")
            self.search_btn.setEnabled(True)

        def on_error(error_msg):
            self.show_error(error_msg)
            self.repo_worker = None
            self.search_btn.setText("Search")
            self.search_btn.setEnabled(True)

        self.repo_worker.finished.connect(on_finished)
        self.repo_worker.error.connect(on_error)
        self.repo_worker.start()

    def on_repos_loaded(self, repos):
        self.repos_all = repos
        self.display_current_page()
        self.clone_btn.setEnabled(True)

    def get_per_page(self):
        try:
            return int(self.per_page_input.text())
        except:
            return 100

    def display_current_page(self):
        self.result_list.clear()
        self.prev_btn.setEnabled(self.current_page > 1)

        per_page = self.get_per_page()
        start_idx = (self.current_page - 1) * per_page
        end_idx = start_idx + per_page
        page_repos = self.repos_all[start_idx:end_idx]

        for repo in page_repos:
            item_widget = RepoListItem(repo)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.result_list.addItem(list_item)
            self.result_list.setItemWidget(list_item, item_widget)

        total_pages = (len(self.repos_all) + per_page - 1) // per_page
        self.page_label.setText(f"Страница {self.current_page} из {total_pages or 1}")
        self.next_btn.setEnabled(end_idx < len(self.repos_all))

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()

    def next_page(self):
        per_page = self.get_per_page()
        if (self.current_page * per_page) < len(self.repos_all):
            self.current_page += 1
            self.display_current_page()

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
