import sys
import json
import os
import requests
from git import Repo
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
    QLineEdit, QLabel, QListWidget, QCheckBox, QComboBox, QFileDialog,
    QMessageBox, QProgressBar, QHBoxLayout, QScrollArea, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal

class RepoWorker(QThread):
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, search_type, **kwargs):
        super().__init__()
        self.search_type = search_type
        self.params = kwargs

    def run(self):
        try:
            if self.search_type == 'user':
                repos = self.get_user_repos(**self.params)
            else:
                repos = self.get_language_repos(**self.params)
                
            self.finished.emit(repos)
        except Exception as e:
            self.error.emit(str(e))

    def get_user_repos(self, username, token=None):
        url = f"https://api.github.com/users/{username}/repos"
        headers = {"Authorization": f"token {token}"} if token else {}
        repos = []
        page = 1
        while True:
            params = {"page": page, "per_page": 100}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return [{"name": r["name"], "owner": r["owner"]["login"], 
                 "stars": r["stargazers_count"], "url": r["html_url"]} 
                for r in repos]

    def get_language_repos(self, language, sort_by, order, token=None):
        url = "https://api.github.com/search/repositories"
        headers = {"Authorization": f"token {token}"} if token else {}
        params = {
            "q": f"language:{language}",
            "sort": sort_by,
            "order": order,
            "per_page": 100,
            "page": 1
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return [{"name": r["name"], "owner": r["owner"]["login"], 
                 "stars": r["stargazers_count"], "url": r["html_url"]} 
                for r in response.json()["items"]]

class CloneWorker(QThread):
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, repo_url, branch, target_dir):
        super().__init__()
        self.repo_url = repo_url
        self.branch = branch
        self.target_dir = target_dir

    def run(self):
        try:
            parts = self.repo_url.rstrip('/').split('/')
            repo_name = parts[-1].replace('.git', '')
            owner = parts[-2]
            
            repo_dir = os.path.join(self.target_dir, f"{owner}-{repo_name}")
            
            if not os.path.exists(repo_dir):
                Repo.clone_from(self.repo_url, repo_dir, branch=self.branch)
                self.progress.emit(f"Успешно: {repo_name}")
            else:
                self.progress.emit(f"Пропущен: {repo_name} (уже существует)")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Repo Downloader")
        self.setGeometry(100, 100, 800, 600)
        
        self.token = None
        self.repos = []
        self.selected_repos = []
        
        self.setup_ui()
        self.clone_workers = []
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
        self.token = self.token_input.text() or None
        self.result_list.clear()
        
        if self.mode_combo.currentIndex() == 0:
            params = {
                "language": self.language_input.text() or "Verilog",
                "sort_by": self.sort_combo.currentText(),
                "order": self.order_combo.currentText(),
                "token": self.token
            }
            self.worker = RepoWorker('language', **params)
        else:
            params = {
                "username": self.username_input.text(),
                "token": self.token
            }
            self.worker = RepoWorker('user', **params)
            
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
                repo_info['branch'] = item_widget.getSelectedBranch()
                self.selected_repos.append(repo_info)

    def start_cloning(self):
        self.selected_repos = []
        for i in range(self.result_list.count()):
            list_item = self.result_list.item(i)
            item_widget = self.result_list.itemWidget(list_item)
            if item_widget.isChecked():
                repo_info = item_widget.repo_info
                repo_info['branch'] = item_widget.getSelectedBranch()
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
            worker = CloneWorker(
                repo['url'], 
                repo['branch'], 
                self.clone_dir
            )
            worker.finished.connect(self.update_progress)
            worker.finished.connect(self.handle_clone_finished)
            worker.error.connect(self.show_error)
            self.clone_workers.append(worker)
            worker.start()

    def update_progress(self):
        current = self.progress_bar.value()
        self.progress_bar.setValue(current + 1)

    def clone_finished(self):
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Complete", "Cloning finished!")
    
    def handle_clone_finished(self):
        if all(not worker.isRunning() for worker in self.clone_workers):
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "Complete", "Cloning finished!")

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

class RepoListItem(QWidget):
    def __init__(self, repo_info):
        super().__init__()
        self.repo_info = repo_info
        self.checkbox = QCheckBox()
        self.checkbox.setText(f"{repo_info['name']} by {repo_info['owner']} (★{repo_info['stars']})")
        
        self.branch_combo = QComboBox()
        self.branch_combo.addItems(["main", "master", "dev"])
        
        layout = QHBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.branch_combo)
        layout.addStretch()
        self.setLayout(layout)
        
    def isChecked(self):
        return self.checkbox.isChecked()
        
    def getSelectedBranch(self):
        return self.branch_combo.currentText()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())