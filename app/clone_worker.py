import os
from git import Repo
from PySide6.QtCore import QThread, Signal


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
            parts = self.repo_url.rstrip("/").split("/")
            repo_name = parts[-1].replace(".git", "")
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
