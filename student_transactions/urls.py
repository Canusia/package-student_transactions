"""
    Student Transaction URL Configuration
"""
from django.urls import path, include
from django.contrib.auth.decorators import user_passes_test

from rest_framework import routers

from cis.utils import user_has_cis_role

from .views.api import StudentTransactionViewSet
from .views.ce import (
    index,
    manage_debit,
    manage_scholarship,
    manage_refund,
    manage_payment,
    delete,
    download_receipt_pdf,
    transaction_summary
)

app_name = 'student_transactions'
router = routers.DefaultRouter()

ROUTER_VS = {
    'transactions': StudentTransactionViewSet,
}

for router_key in ROUTER_VS.keys():
    router.register(
        router_key,
        ROUTER_VS[router_key],
        basename=router_key
    )

urlpatterns = [
    path(
        'api/',
        include(router.urls)
    ),
    path(
        'api/summary/',
        user_passes_test(user_has_cis_role, login_url='/')(transaction_summary),
        name='transaction_summary'
    ),

    path(
        'transactions/',
        user_passes_test(user_has_cis_role, login_url='/')(index),
        name='index'
    ),
    path(
        'transactions/student/<uuid:student_id>/receipt/',
        download_receipt_pdf,
        name='download_receipt_pdf'
    ),
    path(
        'transactions/manage_scholarship/<uuid:student_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(manage_scholarship),
        name='manage_scholarship'
    ),
    path(
        'transactions/manage_refund/<uuid:student_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(manage_refund),
        name='manage_refund'
    ),
    path(
        'transactions/manage_scholarship/<uuid:student_id>/<uuid:transaction_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(manage_scholarship),
        name='edit_scholarship'
    ),
    path(
        'transactions/manage_payment/<uuid:student_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(manage_payment),
        name='manage_payment'
    ),
    path(
        'transactions/manage_payment/<uuid:student_id>/<uuid:transaction_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(manage_payment),
        name='edit_payment'
    ),
    path(
        'transactions/manage_debit/<uuid:student_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(manage_debit),
        name='manage_debit'
    ),
    path(
        'transactions/manage_debit/<uuid:student_id>/<uuid:transaction_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(manage_debit),
        name='edit_debit'
    ),
    path(
        'transactions/delete/<uuid:student_id>/<uuid:transaction_id>/',
        user_passes_test(user_has_cis_role, login_url='/')(delete),
        name='delete'
    ),
]
