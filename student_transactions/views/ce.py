from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt

from cis.campus_gate import scope_records_by_student_campus
from cis.menu import cis_menu, draw_menu
from cis.models.student import Student

from ..models import StudentTransaction
from ..forms import (
    StudentChargeForm, StudentScholarshipForm, StudentPaymentForm, StudentRefundForm
)
from ..table_configs.resolve import resolve_table_config

# Layout-agnostic default: works whether this module lives at
# student_transactions.views.ce (installed) or
# student_transactions.student_transactions.views.ce (editable submodule).
_PKG_CE_TABLE = __package__.rsplit('.', 1)[0] + '.table_configs.ce_transactions'


def _can_access_student_receipt(request, student):
    """Check if the current user/session can access the student's receipt."""
    from cis.utils import user_has_cis_role, user_has_student_role

    # CIS admins can access any receipt
    if user_has_cis_role(request.user):
        return True

    # Students can only access their own receipt
    if user_has_student_role(request.user):
        return student.user == request.user

    # Session-based access (e.g., anonymous checkout)
    record_key = request.session.get('record_key')
    return record_key and record_key == str(student.id)


def download_receipt_pdf(request, student_id):
    from django.http import HttpResponseNotFound

    student = get_object_or_404(Student, pk=student_id)

    if not _can_access_student_receipt(request, student):
        return HttpResponseNotFound("Unable to process request")

    pdf = student.generate_account_statement(request=request)

    if request.GET.get('mode') == 'page':
        return HttpResponse(pdf)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="student_receipt_{student.user.id}.pdf"'
    return response
download_receipt_pdf.login_required = False


def delete(request, student_id, transaction_id):
    transaction = get_object_or_404(
        StudentTransaction,
        pk=transaction_id
    )

    if transaction.student.id != student_id:
        return JsonResponse(
            {
                'message': 'Unable to find transaction for student'
            },
            status=400
        )
    transaction.delete()
    return JsonResponse(
        {
            'status': 'success',
            'message': 'Successfully deleted transaction'
        }
    )


@xframe_options_exempt
def manage_payment(request, student_id, transaction_id='-1'):

    template = 'transactions/manage_payment.html'
    form = StudentPaymentForm(student_id, transaction_id)

    record = None
    if transaction_id != '-1':
        record = get_object_or_404(StudentTransaction, pk=transaction_id)
        if not record.description:
            record.description = ''

        if record.is_refund:
            return manage_refund(request, student_id, transaction_id)

        if "scholarship" in record.description.lower():
            return manage_scholarship(request, student_id, transaction_id)

    if request.method == 'POST':
        form = StudentPaymentForm(
            student_id,
            transaction_id,
            request.POST
        )

        if form.is_valid():
            form.save(request, True)
            return JsonResponse(
                {
                    'status': 'success',
                    'message': 'Successfully saved payment'
                }
            )
        else:
            return JsonResponse(
                {
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.get_json_data()
                },
                status=400
            )

    return render(
        request,
        template, {
            'page_title': "Manage Transaction",
            'form': form,
            'record': record,
            'student_id': student_id,
            'transaction_id': transaction_id,
        }
    )


@xframe_options_exempt
def manage_scholarship(request, student_id, transaction_id='-1'):

    template = 'transactions/manage_scholarship.html'
    form = StudentScholarshipForm(student_id, transaction_id)

    record = None
    if transaction_id != '-1':
        record = get_object_or_404(StudentTransaction, pk=transaction_id)

    if request.method == 'POST':
        form = StudentScholarshipForm(
            student_id,
            transaction_id,
            request.POST
        )

        if form.is_valid():
            form.save(request, True)
            return JsonResponse(
                {
                    'status': 'success',
                    'message': 'Successfully saved scholarship'
                }
            )
        else:
            return JsonResponse(
                {
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.get_json_data()
                },
                status=400
            )

    return render(
        request,
        template, {
            'page_title': "Manage Student Scholarship",
            'form': form,
            'record': record,
            'student_id': student_id,
            'transaction_id': transaction_id,
        }
    )


@xframe_options_exempt
def manage_refund(request, student_id, transaction_id='-1'):

    template = 'transactions/manage_refund.html'
    form = StudentRefundForm(student_id, transaction_id)

    record = None
    if transaction_id != '-1':
        record = get_object_or_404(StudentTransaction, pk=transaction_id)

    if request.method == 'POST':
        form = StudentRefundForm(
            student_id,
            transaction_id,
            request.POST
        )

        if form.is_valid():
            form.save(request, True)
            return JsonResponse(
                {
                    'status': 'success',
                    'message': 'Successfully saved refund'
                }
            )
        else:
            return JsonResponse(
                {
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.get_json_data()
                },
                status=400
            )

    return render(
        request,
        template, {
            'page_title': "Manage Student Refund",
            'form': form,
            'record': record,
            'student_id': student_id,
            'transaction_id': transaction_id,
        }
    )


@xframe_options_exempt
def manage_debit(request, student_id, transaction_id='-1'):

    template = 'transactions/manage_debit.html'
    form = StudentChargeForm(student_id, transaction_id)

    record = None
    if transaction_id != '-1':
        record = get_object_or_404(StudentTransaction, pk=transaction_id)

    if request.method == 'POST':
        form = StudentChargeForm(
            student_id,
            transaction_id,
            request.POST
        )

        if form.is_valid():
            form.save(request, True)
            return JsonResponse(
                {
                    'status': 'success',
                    'message': 'Successfully saved charge'
                }
            )
        else:
            return JsonResponse(
                {
                    'message': 'Please correct the errors and try again',
                    'errors': form.errors.get_json_data()
                },
                status=400
            )

    return render(
        request,
        template, {
            'page_title': "Manage Student Charge",
            'form': form,
            'record': record,
            'student_id': student_id,
            'transaction_id': transaction_id,
        }
    )


def _open_manage_url(request, manage_url_name, edit_url_name):
    """Build an 'open' outcome JSON for the given row action's manage/edit view.

    Reads student_id/transaction_id from POST (falling back to GET), and picks
    the edit-url variant when a transaction_id is present. The 'open' outcome
    opens the manage/receipt view in a new browser tab (see
    ce_transactions_table.js's handleRowActionResponse, which calls
    window.open(url, '_blank')) -- not an iframe modal.
    """
    student_id = request.POST.get('student_id') or request.GET.get('student_id')
    transaction_id = request.POST.get('transaction_id') or request.GET.get('transaction_id')

    if not student_id:
        return JsonResponse({
            'outcome': 'alert',
            'status': 'error',
            'title': 'Error',
            'message': 'No student selected.',
        }, status=400)

    if transaction_id and transaction_id != '-1':
        url = reverse(
            f'student_transactions:{edit_url_name}',
            kwargs={'student_id': student_id, 'transaction_id': transaction_id})
    else:
        url = reverse(
            f'student_transactions:{manage_url_name}',
            kwargs={'student_id': student_id})

    return JsonResponse({'outcome': 'open', 'url': url})


def manage_payment_action(request):
    return _open_manage_url(request, 'manage_payment', 'edit_payment')


def manage_scholarship_action(request):
    return _open_manage_url(request, 'manage_scholarship', 'edit_scholarship')


def manage_refund_action(request):
    return _open_manage_url(request, 'manage_refund', 'edit_refund')


def download_receipt_action(request):
    student_id = request.POST.get('student_id') or request.GET.get('student_id')
    if not student_id:
        return JsonResponse({
            'outcome': 'alert',
            'status': 'error',
            'title': 'Error',
            'message': 'No student selected.',
        }, status=400)

    url = reverse('student_transactions:download_receipt_pdf', kwargs={'student_id': student_id})
    return JsonResponse({'outcome': 'open', 'url': url})


def do_bulk_action(request):
    from ..actions import transaction_actions

    action = request.POST.get('action') or request.GET.get('action')

    if action == 'delete_transactions':
        ids = request.POST.getlist('ids[]')
        qs = scope_records_by_student_campus(
            StudentTransaction.objects.filter(pk__in=ids), request.user)
        deleted, failed = 0, 0
        for txn in qs:
            try:
                txn.delete()
                deleted += 1
            except Exception:
                failed += 1
        msg = f'Deleted {deleted} transaction(s).'
        if failed:
            msg += f' {failed} could not be deleted.'
        return JsonResponse({
            'outcome': 'call',
            'fn': 'onBulkActionComplete',
            'args': {
                'title': 'Delete Transactions',
                'message': msg,
                'status': 'success' if not failed else 'warning',
            },
        })

    return transaction_actions.dispatch(request, action)
do_bulk_action.login_required = True


def transaction_summary(request):
    """Return transaction summary grouped by label (type)."""
    from django.db.models import Count, Sum

    queryset = StudentTransaction.objects.all()

    # Apply term filter if provided
    term_id = request.GET.get('term_id')
    if term_id:
        queryset = queryset.filter(term__id=term_id)

    # Build label to display name mapping
    label_map = {}
    label_map.update(dict(StudentTransaction.DEBIT_TRANSACTION_TYPES))
    label_map.update(dict(StudentTransaction.PAYMENT_TYPES))
    label_map.update(dict(StudentTransaction.SCHOLARSHIP_TYPES))
    label_map.update(dict(StudentTransaction.REFUND_TYPES))

    # Group by label and t_type, get count and sum
    summary = queryset.values('label', 't_type').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('t_type', 'label')

    items = []
    debit_total = 0
    credit_total = 0

    for item in summary:
        label = item['label']
        t_type = item['t_type']
        total = item['total'] or 0

        items.append({
            'label': label,
            'display': label_map.get(label, label),
            't_type': t_type,
            'count': item['count'],
            'total': round(total, 2)
        })

        if t_type == 'debit':
            debit_total += total
        else:
            credit_total += total

    return JsonResponse({
        'items': items,
        'totals': {
            'debit': round(debit_total, 2),
            'credit': round(credit_total, 2),
            'net': round(debit_total - credit_total, 2)
        }
    })


def index(request):
    from cis.models.term import Term
    from cis.campus_gate import get_accessible_campuses
    from cis.utils import get_default_campus
    # Lazy import: actions.py imports views.ce (to wrap manage_payment_action
    # etc. as handlers), so importing it at module level here would create a
    # circular import.
    from ..actions import transaction_actions

    menu = draw_menu(cis_menu, 'students', 'transactions')
    template = 'transactions/index.html'

    terms = Term.objects.all().order_by('-code')

    row_actions = {}
    for group in transaction_actions.for_scope('detail', request.user).values():
        for slug, action in group['actions'].items():
            row_actions[slug] = {'label': action['label'], 'icon': action.get('icon')}

    cfg_mod = resolve_table_config('ce_transactions_table', _PKG_CE_TABLE)
    table = cfg_mod.build_config(
        variant='ce_index',
        api_url='/ce/student_transactions/api/transactions/?format=datatables',
        summary_api_url='/ce/student_transactions/api/summary/',
        bulk_actions={
            'delete_transactions': {
                'label': 'Delete Selected', 'icon': 'fas fa-trash',
                'btn_class': 'btn-danger',
                'confirm': 'Delete selected transaction(s)? This cannot be undone.',
            },
        },
        bulk_actions_url=reverse('student_transactions:do_bulk_action'),
        row_actions=row_actions,
    )

    return render(
        request,
        template, {
            'menu': menu,
            'page_title': 'Student Transactions',
            'terms': terms,
            'accessible_campuses': get_accessible_campuses(request.user),
            'default_campus': get_default_campus(request.user),
            'table': table,
        }
    )
