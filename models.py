"""Editable-submodule proxy — re-export the inner package's models so host code
`from student_transactions.models import StudentTransaction` resolves in the dev
layout. In the pip-installed layout the inner package IS `student_transactions`
and this loose module is not part of the wheel (packages=find: ships only the
inner package)."""
from student_transactions.student_transactions.models import *  # noqa: F401,F403
from student_transactions.student_transactions.models import (  # noqa: F401
    StudentTransaction,
    StudentTransactionManager,
)
