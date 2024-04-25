from django.core.management import BaseCommand

from ingestion.models import UpdateConsumption


class CommandAsLogger:
    """A very brittle Logger interface"""

    def __init__(self, command: BaseCommand):
        self._command = command

    def info(self, *args, **kwargs):
        self._command.stdout.write(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self._command.stdout.write(*args, **kwargs)

    def error(self, *args, **kwargs):
        self._command.stderr.write(*args, **kwargs)

    def exception(self, *args, **kwargs):
        self._command.stderr.write(*args, **kwargs)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--all-rows',
            action='store_true',
        )
        parser.add_argument(
            '--pretend',
            action='store_true',
        )

    def handle(self, all_rows: bool, pretend: bool, **kwargs):
        update = UpdateConsumption(
            logger=CommandAsLogger(self),
            pretend=pretend,
        )

        update.update_rows(all_rows)
