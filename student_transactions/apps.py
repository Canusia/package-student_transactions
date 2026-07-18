from django.apps import AppConfig


class StudentTransactionsConfig(AppConfig):
    """pip-installed layout: importable as `student_transactions`."""
    name = 'student_transactions'

    def ready(self):
        from . import signals  # noqa: F401


class DevStudentTransactionsConfig(AppConfig):
    """editable-submodule layout: importable as `student_transactions.student_transactions`."""
    name = 'student_transactions.student_transactions'

    def ready(self):
        from . import signals  # noqa: F401
