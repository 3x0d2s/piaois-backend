import getpass
from argparse import ArgumentParser
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from pymongo.errors import PyMongoError


class Command(BaseCommand):
    help = "Create a staff operator with an interactive password, without public registration"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("username")
        parser.add_argument("--email", default="")

    def handle(self, *args: Any, **options: Any) -> None:
        model = get_user_model()
        user = model(
            username=options["username"],
            email=options["email"],
            is_staff=True,
            is_superuser=False,
        )
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Password again: "):
            raise CommandError("Passwords do not match")
        try:
            user.full_clean(exclude=["password"])
            validate_password(password, user)
            user.set_password(password)
            user.save(force_insert=True)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from None
        except DatabaseError, PyMongoError:
            raise CommandError(
                "Cannot create operator: database unavailable or username already exists"
            ) from None
        self.stdout.write(self.style.SUCCESS(f"Operator {user.get_username()} created"))
