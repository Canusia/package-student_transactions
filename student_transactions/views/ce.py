from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt

from cis.menu import cis_menu, draw_menu
from cis.models.student import Student

from ..models import StudentTransaction
from ..forms import (
    StudentChargeForm, StudentScholarshipForm, StudentPaymentForm, StudentRefundForm
)


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

    menu = draw_menu(cis_menu, 'students', 'transactions')
    template = 'transactions/index.html'

    terms = Term.objects.all().order_by('-code')

    return render(
        request,
        template, {
            'menu': menu,
            'page_title': 'Student Transactions',
            'api_url': '/ce/student_transactions/api/transactions/?format=datatables',
            'summary_api_url': '/ce/student_transactions/api/summary/',
            'terms': terms,
            'accessible_campuses': get_accessible_campuses(request.user),
            'default_campus': get_default_campus(request.user),
        }
    )
