import argparse
from getpass import getpass

from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.identity.passwords import hash_password
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactively provision a staff account.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument(
        "--role",
        required=True,
        choices=["controller", "administrator"],
    )
    args = parser.parse_args()

    try:
        data = ProvisionStaffInput.model_validate(
            {
                "username": args.username,
                "display_name": args.display_name,
                "role": args.role,
            }
        )
    except ValueError as error:
        parser.error(str(error))

    settings = Settings()
    if settings.database_url is None:
        parser.error("Configure the database URL before provisioning.")

    password = getpass("Password (15–128 characters): ")
    confirmation = getpass("Confirm password: ")

    if password != confirmation:
        parser.error("Passwords do not match.")

    try:
        encoded_password = hash_password(password)
    except ValueError as error:
        parser.error(str(error))

    del password
    del confirmation

    engine = create_db_engine(settings)

    try:
        with Session(engine) as session:
            with session.begin():
                user = provision_staff_user(session, data, encoded_password)
                user_id = user.id
                username = user.username

        print(f"Staff account created: {username}")
        print(f"User ID: {user_id}")
        print(f"Role: {data.role.value}")
    except ValueError as error:
        parser.exit(status=2, message=f"Provisioning failed: {error}\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
