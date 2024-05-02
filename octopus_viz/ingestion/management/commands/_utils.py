import logging

from django.core.management import BaseCommand


class CommandAsLogger:
    """A very brittle Logger interface"""

    def __init__(self, command: BaseCommand, *, log_level: int = logging.INFO):
        self._command = command
        self.log_level: int = log_level

    def debug(self, *args, **kwargs):
        if self.log_level >= logging.DEBUG:
            self._command.stdout.write(*args, **kwargs)

    def info(self, *args, **kwargs):
        if self.log_level >= logging.INFO:
            self._command.stdout.write(*args, **kwargs)

    def warning(self, *args, **kwargs):
        if self.log_level >= logging.WARNING:
            self._command.stdout.write(*args, **kwargs)

    def error(self, *args, **kwargs):
        if self.log_level >= logging.ERROR:
            self._command.stderr.write(*args, **kwargs)

    def exception(self, *args, **kwargs):
        # TODO(tr) print the exception state
        self._command.stderr.write(*args, **kwargs)
