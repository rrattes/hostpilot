import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.auth.security import hash_password, validate_password_policy
from app.db.models import Role, User
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the initial HostPilot admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", default="HostPilot Admin")
    parser.add_argument("--password", help="Prefer interactive entry outside automated setup.")
    args = parser.parse_args()

    password = args.password or getpass("Password: ")
    confirm_password = args.password or getpass("Confirm password: ")
    if password != confirm_password:
        raise SystemExit("Passwords do not match.")
    password_errors = validate_password_policy(password)
    if password_errors:
        raise SystemExit(" ".join(password_errors))

    email = args.email.lower()

    with SessionLocal() as db:
        admin_role = db.scalar(select(Role).where(Role.slug == "admin"))
        if admin_role is None:
            raise SystemExit("Admin role not found. Run `alembic upgrade head` first.")

        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                display_name=args.display_name,
                password_hash=hash_password(password),
                is_active=True,
                is_superuser=True,
                roles=[admin_role],
            )
            db.add(user)
            action = "created"
        else:
            user.display_name = args.display_name
            user.password_hash = hash_password(password)
            user.is_active = True
            user.is_superuser = True
            if admin_role not in user.roles:
                user.roles.append(admin_role)
            action = "updated"

        db.commit()

    print(f"Admin user {action}: {email}")


if __name__ == "__main__":
    main()
