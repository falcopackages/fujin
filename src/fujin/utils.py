import json
import urllib.request
from functools import wraps

from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TextColumn


def with_progress(description, pass_progress=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task(description, total=None)
                if pass_progress:
                    kwargs["progress"] = lambda desc: progress.update(task, description=desc)
                result = func(*args, **kwargs)
                progress.update(task, completed=True)
                progress.console.print(f"[green]{description} completed!")
                return result

        return wrapper

    return decorator


def _get_asset_id(token, owner, repo, project_name):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        assets = data["assets"]
    for asset in assets:
        if asset["name"] == f"{project_name}-x86_64-linux":
            return asset["id"]
    msg = f"Asset not found with name {project_name}-x86_64-linux"
    raise Exception(msg)


def curl_binary_download_cmd(*, owner, repo, project_name=None, token=None):
    curl = "curl -L -H 'Accept: application/octet-stream' "
    project_name = project_name or repo
    if not token:
        return f"{curl} https://github.com/{owner}/{repo}/releases/latest/download/{project_name}-x86_64-linux"
    asset_id = _get_asset_id(token, owner, repo, project_name)
    return (
        f"{curl} -H 'Authorization: Bearer {token}' "
        f"-H 'X-GitHub-Api-Version: 2022-11-28' "
        f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"
    )
