"""Package-owned action registry for CE transaction row actions.

Registers the row-level (scope=['detail']) actions used by the CE
transactions DataTable's Actions dropdown. Each handler opens the existing
manage/receipt view in the modal-iframe via the 'open' outcome, mirroring
cis.actions.term / cis.views.student's download_student_pdf pattern.
"""
from .action_registry import ActionRegistry
from .views import ce as ce_views

transaction_actions = ActionRegistry()

transaction_actions.action(
    'transactions', label='Manage Payment', scope=['detail'],
    slug='manage_payment', icon='fas fa-money-bill', method='ajax',
)(ce_views.manage_payment_action)

transaction_actions.action(
    'transactions', label='Manage Scholarship', scope=['detail'],
    slug='manage_scholarship', icon='fas fa-graduation-cap', method='ajax',
)(ce_views.manage_scholarship_action)

transaction_actions.action(
    'transactions', label='Manage Refund', scope=['detail'],
    slug='manage_refund', icon='fas fa-undo', method='ajax',
)(ce_views.manage_refund_action)

transaction_actions.action(
    'transactions', label='Download Receipt', scope=['detail'],
    slug='download_receipt', icon='fas fa-file-pdf', method='ajax',
)(ce_views.download_receipt_action)
