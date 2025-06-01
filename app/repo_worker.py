import requests
from PySide6.QtCore import QThread, Signal


class RepoWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, search_type, **kwargs):
        super().__init__()
        self.search_type = search_type
        self.params = kwargs

    def run(self):
        try:
            if self.search_type == "user":
                repos = self.get_user_repos(**self.params)
            else:
                repos = self.get_language_repos(**self.params)
            self.finished.emit(repos)
        except Exception as e:
            self.error.emit(str(e))

    def get_branches(self, repo_url, token=None):
        try:
            owner = repo_url.split("/")[-2]
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            url = f"https://api.github.com/repos/{owner}/{repo_name}/branches"
            headers = {"Authorization": f"token {token}"} if token else {}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return [branch["name"] for branch in response.json()]
        except Exception as e:
            print(f"Ошибка при получении веток для {repo_url}: {e}")
            return ["main"]

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
        result = []
        for r in repos:
            branches = self.get_branches(r["html_url"], token)
            result.append(
                {
                    "name": r["name"],
                    "owner": r["owner"]["login"],
                    "stars": r["stargazers_count"],
                    "url": r["html_url"],
                    "branches": branches,
                }
            )
        return result

    def get_language_repos(self, language, sort_by, order, token=None):
        url = "https://api.github.com/search/repositories"
        headers = {"Authorization": f"token {token}"} if token else {}
        params = {
            "q": f"language:{language}",
            "sort": sort_by,
            "order": order,
            "per_page": 100,
            "page": 1,
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        items = response.json()["items"]
        result = []
        for r in items:
            branches = self.get_branches(r["html_url"], token)
            result.append(
                {
                    "name": r["name"],
                    "owner": r["owner"]["login"],
                    "stars": r["stargazers_count"],
                    "url": r["html_url"],
                    "branches": branches,
                }
            )
        return result
