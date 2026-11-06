
import os
import secrets
import hmac

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.getenv(
    "GITHUB_CALLBACK_URL",
    "http://localhost:8000/api/auth/github/callback"
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Temporary in-memory storage for local development.
# We will replace this with persistent encrypted database storage.
oauth_states = set()
user_sessions = {}


@router.get("/github/login")
async def github_login():
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_ID is not configured"
        )

    state = secrets.token_urlsafe(32)
    oauth_states.add(state)

    authorization_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_CALLBACK_URL}"
        f"&state={state}"
    )

    response = RedirectResponse(authorization_url)

    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=600
    )

    return response


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None
):
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub authorization failed: {error}"
        )

    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="Missing authorization code or state"
        )

    cookie_state = request.cookies.get("oauth_state")

    if (
        not cookie_state
        or not hmac.compare_digest(cookie_state, state)
        or state not in oauth_states
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state"
        )

    # Prevent reusing the same state.
    oauth_states.discard(state)

    if not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_CLIENT_SECRET is not configured"
        )

    async with httpx.AsyncClient(timeout=20.0) as client:

        # Exchange authorization code for a GitHub user access token.
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json"
            },
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_CALLBACK_URL
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail="GitHub token exchange failed"
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=502,
                detail=token_data.get(
                    "error_description",
                    "GitHub did not return an access token"
                )
            )

        # Fetch the authenticated GitHub user.
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail="Could not retrieve GitHub user profile"
            )

        github_user = user_response.json()

    # Create an opaque application session.
    session_id = secrets.token_urlsafe(32)

    user_sessions[session_id] = {
        "access_token": access_token,
        "github_user": {
            "id": github_user["id"],
            "login": github_user["login"],
            "name": github_user.get("name"),
            "avatar_url": github_user.get("avatar_url")
        }
    }

    response = RedirectResponse(
        url=f"{FRONTEND_URL}/dashboard",
        status_code=303
    )

    response.delete_cookie("oauth_state")

    response.set_cookie(
        key="patchproof_session",
        value=session_id,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=86400,
        path="/"
    )

    return response


@router.get("/me")
async def get_current_user(request: Request):
    session_id = request.cookies.get("patchproof_session")

    session = user_sessions.get(session_id)

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    return {
        "authenticated": True,
        "user": session["github_user"]
    }


@router.post("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("patchproof_session")

    if session_id:
        user_sessions.pop(session_id, None)

    response = JSONResponse({
        "message": "Logged out successfully"
    })

    response.delete_cookie(
        key="patchproof_session",
        path="/"
    )

    return response
