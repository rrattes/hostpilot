from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import hash_password, verify_password
from app.db.base import Base
from app.db.models import Role, User
from app.scripts import bootstrap_admin


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_function() -> None:
    Base.metadata.create_all(bind=engine)
    bootstrap_admin.SessionLocal = TestingSessionLocal
    with TestingSessionLocal() as db:
        db.add(Role(slug="admin", name="Admin"))
        db.commit()


def teardown_function() -> None:
    Base.metadata.drop_all(bind=engine)


def _admin_user() -> User:
    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert user is not None
        db.expunge(user)
        return user


def test_bootstrap_creates_admin_when_missing(capsys) -> None:
    bootstrap_admin.main(
        [
            "--email",
            "ADMIN@EXAMPLE.COM",
            "--display-name",
            "Initial Admin",
            "--password",
            "CreatedPassword123!",
        ]
    )

    user = _admin_user()
    output = capsys.readouterr().out

    assert "Admin user created: admin@example.com" in output
    assert user.display_name == "Initial Admin"
    assert user.is_active is True
    assert user.is_superuser is True
    assert verify_password("CreatedPassword123!", user.password_hash)


def test_existing_admin_does_not_change_password_without_reset_flag(capsys, monkeypatch) -> None:
    with TestingSessionLocal() as db:
        db.add(
            User(
                email="admin@example.com",
                display_name="Existing Admin",
                password_hash=hash_password("OriginalPassword123!"),
                is_active=True,
                is_superuser=True,
            )
        )
        db.commit()

    def fail_if_password_collected(password_arg: str | None) -> str:
        raise AssertionError("Password should not be collected without --reset-password.")

    monkeypatch.setattr(bootstrap_admin, "_collect_password", fail_if_password_collected)

    bootstrap_admin.main(
        [
            "--email",
            "admin@example.com",
            "--display-name",
            "Changed Name",
            "--password",
            "NewPassword123!",
        ]
    )

    user = _admin_user()
    output = capsys.readouterr().out

    assert "Password was not changed" in output
    assert user.display_name == "Existing Admin"
    assert verify_password("OriginalPassword123!", user.password_hash)
    assert not verify_password("NewPassword123!", user.password_hash)


def test_existing_admin_resets_password_only_with_reset_flag(capsys) -> None:
    with TestingSessionLocal() as db:
        db.add(
            User(
                email="admin@example.com",
                display_name="Existing Admin",
                password_hash=hash_password("OriginalPassword123!"),
                is_active=False,
                is_superuser=False,
            )
        )
        db.commit()

    bootstrap_admin.main(
        [
            "--email",
            "admin@example.com",
            "--display-name",
            "Reset Admin",
            "--password",
            "ResetPassword123!",
            "--reset-password",
        ]
    )

    user = _admin_user()
    output = capsys.readouterr().out

    assert "Admin user password reset: admin@example.com" in output
    assert user.display_name == "Reset Admin"
    assert user.is_active is True
    assert user.is_superuser is True
    assert verify_password("ResetPassword123!", user.password_hash)
    assert not verify_password("OriginalPassword123!", user.password_hash)
