"""Editable-submodule proxy for `include('student_transactions.urls')`."""
from student_transactions.student_transactions.urls import (  # noqa: F401
    app_name,
    urlpatterns,
)
