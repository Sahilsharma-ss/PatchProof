import os
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request

from app.routes.auth import user_sessions
from app.services.github_app import get_user_installation_repositories
from app.services.github_app import create_installation_token
router = APIRouter(
    prefix="/api/repositories",
    tags=["Repositories"]
)


@router.get("")
async def get_repositories(request: Request):

    # 1. Get the current application session.
    session_id = request.cookies.get("patchproof_session")
    session = user_sessions.get(session_id)

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Please login with GitHub first."
        )

    # 2. Get authenticated GitHub username.
    github_user = session.get("github_user")

    if not github_user:
        raise HTTPException(
            status_code=401,
            detail="GitHub user information not found."
        )

    github_username = github_user["login"]

    # 3. Fetch repositories through the GitHub App installation.
    try:
        repositories = await get_user_installation_repositories(
            github_username
        )

    except Exception as error:
        print("Repository fetch error:", repr(error))

        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve repositories from GitHub. Check backend logs."
        )

    return {
        "total": len(repositories),
        "repositories": repositories
    }

@router.post("/{repository_id}/clone")
async def clone_repository(
    repository_id: int,
    request: Request
):
    # 1. Authenticate the application session.
    session_id = request.cookies.get("patchproof_session")
    session = user_sessions.get(session_id)

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Please login with GitHub first."
        )

    github_user = session.get("github_user", {})
    github_username = github_user.get("login")

    if not github_username:
        raise HTTPException(
            status_code=401,
            detail="GitHub user information is missing."
        )

    # 2. Retrieve repositories available to this user.
    try:
        repositories = await get_user_installation_repositories(
            github_username
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not verify repository access."
        )

    # 3. Verify the selected repository is accessible.
    selected_repo = next(
        (
            repo for repo in repositories
            if repo["id"] == repository_id
        ),
        None
    )

    if not selected_repo:
        raise HTTPException(
            status_code=403,
            detail="This repository is not accessible through PatchProof."
        )

    installation_id = selected_repo["installation_id"]

    # 4. Generate a token restricted to this repository.
    try:
        token_data = await create_installation_token(
            installation_id,
            repository_ids=[repository_id]
        )

        installation_token = token_data["token"]

    except Exception as error:
        print("Installation token error:", repr(error))
        raise HTTPException(
            status_code=502,
            detail="Could not generate repository access token."
        )

    # 5. Prepare a safe local workspace path.
    workspace_root = Path(
        os.getenv("WORKSPACE_ROOT", "./workspaces")
    )

    if not workspace_root.is_absolute():
        workspace_root = (
            Path(__file__).resolve().parents[2] / workspace_root
        )

    repo_directory = (
        workspace_root
        / str(github_user["id"])
        / str(repository_id)
    )

    repo_directory.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Avoid overwriting an existing clone.
    if repo_directory.exists():
        raise HTTPException(
            status_code=409,
            detail="Repository is already cloned in this workspace."
        )

    # 6. Clone securely without putting the token in the URL
    # or command-line arguments.
    import base64

    credentials = f"x-access-token:{installation_token}"
    encoded_credentials = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("ascii")

    git_environment = os.environ.copy()

    git_environment["GIT_CONFIG_COUNT"] = "1"
    git_environment["GIT_CONFIG_KEY_0"] = "http.extraheader"
    git_environment["GIT_CONFIG_VALUE_0"] = (
        f"AUTHORIZATION: basic {encoded_credentials}"
    )

    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--",
                selected_repo["html_url"],
                str(repo_directory)
            ],
            env=git_environment,
            capture_output=True,
            text=True,
            timeout=600,
            check=False
        )

        if result.returncode != 0:
            raise RuntimeError(
                result.stderr[-2000:]
            )

        # Get the cloned commit SHA.
        commit_result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_directory),
                "rev-parse",
                "HEAD"
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        commit_sha = commit_result.stdout.strip()

        return {
            "message": "Repository cloned successfully.",
            "repository": selected_repo["full_name"],
            "local_path": str(repo_directory.resolve()),
            "commit_sha": commit_sha
        }

    except subprocess.TimeoutExpired:
        import shutil
        shutil.rmtree(repo_directory, ignore_errors=True)

        raise HTTPException(
            status_code=504,
            detail="Repository cloning timed out."
        )

    except Exception as error:
        import shutil
        shutil.rmtree(repo_directory, ignore_errors=True)

        print("Clone error:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Repository cloning failed. Check backend logs."
        )
