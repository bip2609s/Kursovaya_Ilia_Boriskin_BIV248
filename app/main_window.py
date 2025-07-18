import sys
import os
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
from PySide6.QtCore import Qt, Signal

from app.repo_worker import RepoWorker
from app.clone_worker import CloneWorker
from app.repo_list_item import RepoListItem


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Repo Downloader")
        self.setGeometry(100, 100, 800, 600)
        self.token = None
        self.repos_all = []
        self.current_page = 1
        self.per_page = 100
        self.selected_repos = []
        self.setup_ui()
        self.load_stylesheet()
        self.clone_workers = []
        self.repo_worker = None
        self.cached_pages = {}
        self.total_pages = 1
        self.current_search_params = None

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

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Search by Language", "Search by User"])
        self.layout.addWidget(self.mode_combo)

        self.param_layout = QVBoxLayout()
        self.language_input = QLineEdit(placeholderText="Language (e.g. Python)")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["stars", "forks", "updated"])
        self.order_combo = QComboBox()
        self.order_combo.addItems(["desc", "asc"])
        self.per_page_input = QLineEdit("50")
        self.username_input = QLineEdit(placeholderText="GitHub username")

        self.token_input = QLineEdit(placeholderText="GitHub token (optional)")
        self.token_input.setEchoMode(QLineEdit.Password)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.start_search)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Назад")
        self.next_btn = QPushButton("Вперёд")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)

        self.page_label = QLabel("Страница 1 из 1")
        self.result_list = QListWidget()
        self.result_list.itemChanged.connect(self.update_selection)

        self.clone_btn = QPushButton("Clone Selected")
        self.clone_btn.setEnabled(False)
        self.clone_btn.clicked.connect(self.start_cloning)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.select_all_current_btn = QPushButton("Select All on Current Page")
        self.select_all_loaded_btn = QPushButton("Select All on Loaded Pages")
        self.select_all_current_btn.clicked.connect(self.select_all_current)
        self.select_all_loaded_btn.clicked.connect(self.select_all_loaded)

        self.layout.addLayout(self.param_layout)
        self.layout.addWidget(self.token_input)
        self.layout.addWidget(self.search_btn)
        self.layout.addWidget(self.select_all_current_btn)
        self.layout.addWidget(self.select_all_loaded_btn)
        self.layout.addLayout(nav_layout)
        self.layout.addWidget(self.page_label)
        self.layout.addWidget(self.result_list)
        self.layout.addWidget(self.clone_btn)
        self.layout.addWidget(self.progress_bar)
        self.central_widget.setLayout(self.layout)

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
            return

        self.token = self.token_input.text() or None
        self.result_list.clear()
        self.current_page = 1
        self.cached_pages = {}
        self.total_pages = 1

        self.search_btn.setText("Поиск...")
        self.search_btn.setEnabled(False)

        if self.mode_combo.currentIndex() == 0:
            search_params = {
                "type": "language",
                "language": self.language_input.text() or "Verilog",
                "sort_by": self.sort_combo.currentText(),
                "order": self.order_combo.currentText(),
                "token": self.token,
            }
        else:
            search_params = {
                "type": "user",
                "username": self.username_input.text(),
                "token": self.token,
            }

        self.current_search_params = search_params
        self.load_page(self.current_page)

    def load_page(self, page):
        if page in self.cached_pages:
            self.display_page(page)
            return

        per_page = self.get_per_page()
        params = self.current_search_params.copy()
        params["page"] = page
        params["per_page"] = per_page

        if params["type"] == "language":
            self.repo_worker = RepoWorker(
                "language",
                language=params["language"],
                sort_by=params["sort_by"],
                order=params["order"],
                token=params["token"],
                page=page,
                per_page=per_page,
            )
        else:
            self.repo_worker = RepoWorker(
                "user",
                username=params["username"],
                token=params["token"],
                page=page,
                per_page=per_page,
            )

        def on_finished(repos):
            self.cached_pages[page] = repos
            self.display_page(page)
            self.repo_worker = None
            self.search_btn.setText("Search")
            self.search_btn.setEnabled(True)

            if repos:
                if params["type"] == "language" and hasattr(
                    self.repo_worker, "total_count"
                ):
                    total_repos = self.repo_worker.total_count
                    self.total_pages = (total_repos + per_page - 1) // per_page
                else:
                    if len(repos) < per_page:
                        self.total_pages = page
                    else:
                        self.total_pages = (
                            page + 1
                        )
                        self.next_btn.setEnabled(True)

            else:
                self.total_pages = 1

            self.page_label.setText(
                f"Страница {self.current_page} из {self.total_pages}"
            )

        def on_error(error_msg):
            self.show_error(error_msg)
            self.repo_worker = None
            self.search_btn.setText("Search")
            self.search_btn.setEnabled(True)

        self.repo_worker.finished.connect(on_finished)
        self.repo_worker.error.connect(on_error)
        self.repo_worker.start()

    def get_per_page(self):
        try:
            return int(self.per_page_input.text())
        except:
            return 50

    def display_page(self, page):
        self.result_list.clear()
        self.prev_btn.setEnabled(page > 1)
        self.next_btn.setEnabled(page < self.total_pages)
        repos = self.cached_pages.get(page, [])
        for repo in repos:
            is_selected = repo.get("selected", False)
            item_widget = RepoListItem(repo)
            item_widget.setChecked(is_selected)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())

            item_widget.stateChanged.connect(self.update_selection)

            self.result_list.addItem(list_item)
            self.result_list.setItemWidget(list_item, item_widget)
            item_widget.stateChanged.connect(self.update_selection)

    def save_current_page_state(self):
        if self.current_page not in self.cached_pages:
            return
            
        # Получаем список репозиториев текущей страницы
        current_repos = self.cached_pages[self.current_page]
        
        # Проходим по всем виджетам в списке
        for i in range(self.result_list.count()):
            item = self.result_list.item(i)
            widget = self.result_list.itemWidget(item)
            if widget and i < len(current_repos):
                # Сохраняем состояние чекбокса
                current_repos[i]["selected"] = widget.isChecked()

    def prev_page(self):
        self.save_current_page_state()
        if self.current_page > 1:
            self.current_page -= 1
            self.load_page(self.current_page)
            self.page_label.setText(
                f"Страница {self.current_page} из {self.total_pages}"
            )

    def next_page(self):
        self.save_current_page_state()
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_page(self.current_page)
            self.page_label.setText(
                f"Страница {self.current_page} из {self.total_pages}"
            )

    def select_all_current(self):
        current_repos = self.cached_pages.get(self.current_page, [])

        if not current_repos:
            return

        all_selected = all(repo.get("selected", False) for repo in current_repos)

        for repo in current_repos:
            repo["selected"] = not all_selected

        self.display_page(self.current_page)
        self.update_selection()

    def select_all_loaded(self):
        if not self.cached_pages:
            return

        all_selected = True
        for page in self.cached_pages.values():
            for repo in page:
                if not repo.get("selected", False):
                    all_selected = False
                    break
            if not all_selected:
                break

        for page in self.cached_pages.values():
            for repo in page:
                repo["selected"] = not all_selected

        self.display_page(self.current_page)
        self.update_selection()

    def update_selection(self):
        self.selected_repos = []
        for i in range(self.result_list.count()):
            list_item = self.result_list.item(i)
            item_widget = self.result_list.itemWidget(list_item)
            if item_widget.isChecked():
                repo_info = item_widget.repo_info
                repo_info["branch"] = item_widget.getSelectedBranch()
                self.selected_repos.append(repo_info)
            else:
                repo_info = item_widget.repo_info
                repo_info["selected"] = False
        self.clone_btn.setEnabled(len(self.selected_repos) > 0)

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
