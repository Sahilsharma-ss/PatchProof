import asyncio

from app.services.github_app import (
    generate_app_jwt,
    get_installations,
    create_installation_token
)


async def main():
    print("1. Testing App JWT...")

    token = generate_app_jwt()
    print("JWT generated successfully.")

    print("\n2. Fetching installations...")

    installations = await get_installations()

    for installation in installations:
        account = installation.get("account", {})

        print(
            "Installation ID:",
            installation["id"],
            "| Account:",
            account.get("login")
        )

    if not installations:
        print("No installations found.")
        return

    installation_id = installations[0]["id"]

    print("\n3. Generating installation access token...")

    result = await create_installation_token(installation_id)

    print("Installation token generated successfully.")
    print("Expires at:", result.get("expires_at"))

    # Never print the actual token.


if __name__ == "__main__":
    asyncio.run(main())