
import os
import time
import jwt
import httpx

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GITHUB_API = "https://api.github.com"

APP_ID = os.getenv("GITHUB_APP_ID")
PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")

if not APP_ID:
    raise RuntimeError("GITHUB_APP_ID is missing from .env")

if not PRIVATE_KEY_PATH:
    raise RuntimeError("GITHUB_PRIVATE_KEY_PATH is missing from .env")

private_key_path = Path(PRIVATE_KEY_PATH)

if not private_key_path.is_absolute():
    private_key_path = Path(__file__).resolve().parents[2] / private_key_path

if not private_key_path.is_file():
    raise RuntimeError(
        f"GitHub private key not found: {private_key_path}"
    )

with open(private_key_path, "r", encoding="utf-8") as key_file:
    PRIVATE_KEY = key_file.read()


def generate_app_jwt():
    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),
        "iss": APP_ID
    }

    return jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm="RS256"
    )


async def get_installations():
    app_jwt = generate_app_jwt()

    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{GITHUB_API}/app/installations",
            headers=headers
        )

        response.raise_for_status()

        return response.json()



async def create_installation_token(
    installation_id: int,
    repository_ids: list[int] | None = None
):
    app_jwt = generate_app_jwt()

    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    payload = {}

    if repository_ids:
        payload["repository_ids"] = repository_ids

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers=headers,
            json=payload
        )

        response.raise_for_status()

        return response.json()

async def get_user_installation_repositories(github_username: str):
    """
    Fetch repositories accessible through PatchProof installations
    belonging to the authenticated GitHub user.
    """

    app_jwt = generate_app_jwt()

    app_headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    all_repositories = []

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Get installations of this GitHub App.
        installations_response = await client.get(
            f"{GITHUB_API}/app/installations",
            headers=app_headers,
            params={"per_page": 100}
        )

        installations_response.raise_for_status()

        installations = installations_response.json()

        # Filter installations by GitHub account.
        user_installations = [
            installation
            for installation in installations
            if installation.get("account", {}).get("login", "").lower()
            == github_username.lower()
        ]

        if not user_installations:
            return []

        # Fetch repositories from matching installations.
        for installation in user_installations:

            installation_id = installation["id"]

            token_data = await create_installation_token(
                installation_id
            )

            installation_token = token_data["token"]

            installation_headers = {
                "Authorization": f"Bearer {installation_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }

            page = 1

            while True:

                repo_response = await client.get(
                    f"{GITHUB_API}/installation/repositories",
                    headers=installation_headers,
                    params={
                        "per_page": 100,
                        "page": page
                    }
                )

                repo_response.raise_for_status()

                repo_data = repo_response.json()
                repo_list = repo_data.get("repositories", [])

                for repo in repo_list:
                    all_repositories.append({
                        "id": repo["id"],
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "private": repo["private"],
                        "description": repo.get("description"),
                        "language": repo.get("language"),
                        "default_branch": repo.get("default_branch"),
                        "html_url": repo["html_url"],
                        "installation_id": installation_id
                    })

                if len(repo_list) < 100:
                    break

                page += 1

    return all_repositories
