import uuid

from django.conf import settings
from django.db import models
from django.db.models import JSONField
from django.template import Context, Template
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils import timezone

from cis.validators import validate_email
from mailer import send_html_mail


class StudentTransactionManager(models.Manager):
    def get_1098t_summary(self, student_id, start_date, end_date, configs=None):
        """
        Calculate 1098-T summary for a single student within a date range.

        Args:
            student_id: ID of the student
            start_date: Start datetime for the calendar year
            end_date: End datetime for the calendar year

        Returns:
            dict with 'charges', 'payments', and 'scholarships' totals
        """
        from django.db.models import Sum, Q
        from decimal import Decimal

        charge_types = configs.get('charge_types', ['debit'])
        credit_pay_types = configs.get('credit_pay_types', ['cc', 'check'])
        scholarship_types = configs.get('scholarship_types', ['1', '2', '3'])
        refund_types = configs.get('refund_types', ['1', '2', '3'])

        summary = self.filter(
            student__id=student_id,
            created_on__gte=start_date,
            created_on__lte=end_date
        ).aggregate(
            charges=Sum('amount', filter=Q(t_type__in=charge_types)),
            payments=Sum('amount', filter=Q(t_type='credit', label__in=credit_pay_types)),
            refunds=Sum('amount', filter=Q(t_type='credit', label__in=refund_types)),
            scholarships=Sum('amount', filter=Q(t_type='credit', label__in=scholarship_types))
        )

        # use decimal instead of float for money calculations
        if configs.get('subtract_refunds', False):
            if summary['payments'] is not None and summary['refunds'] is not None:
                summary['payments'] -= abs(summary['refunds'])

        return {
            'charges': Decimal(str(summary['charges'] or 0.0)),
            'payments': Decimal(str(summary['payments'] or 0.0)),
            'scholarships': Decimal(str(summary['scholarships'] or 0.0))
        }

    def get_bulk_1098t_summary(self, student_ids, start_date, end_date, configs=None):
        """
        Calculate 1098-T summaries for multiple students within a date range.

        Args:
            student_ids: List or queryset of student IDs
            start_date: Start datetime for the calendar year
            end_date: End datetime for the calendar year

        Returns:
            dict mapping student_id to summary dict with 'charges', 'payments', 'scholarships'
        """
        from django.db.models import Sum, Q, FloatField
        from django.db.models.functions import Coalesce
        from decimal import Decimal

        charge_types = configs.get('charge_types', ['debit'])
        credit_pay_types = configs.get('credit_pay_types', ['cc', 'check'])
        scholarship_types = configs.get('scholarship_types', ['1', '2', '3'])
        refund_types = configs.get('refund_types', ['1', '2', '3'])

        summaries = self.filter(
            student__id__in=student_ids,
            created_on__gte=start_date,
            created_on__lte=end_date
        ).values('student__id').annotate(
            charges=Coalesce(
                Sum('amount', filter=Q(t_type__in=charge_types)),
                0.0,
                output_field=FloatField()
            ),
            payments=Coalesce(
                Sum('amount', filter=Q(t_type='credit', label__in=credit_pay_types)),
                0.0,
                output_field=FloatField()
            ),
            refunds=Coalesce(
                Sum('amount', filter=Q(t_type='credit', label__in=refund_types)),
                0.0,
                output_field=FloatField()
            ),
            scholarships=Coalesce(
                Sum('amount', filter=Q(t_type='credit', label__in=scholarship_types)),
                0.0,
                output_field=FloatField()
            )
        )

        # Adjust payments by subtracting refunds if configured
        if configs.get('subtract_refunds', False):
            for item in summaries:
                item['payments'] -= abs(item.get('refunds', 0.0))

        # Convert to dict for easy lookup
        return {
            item['student__id']: {
                'charges': Decimal(str(item.get('charges', 0.0))),
                'payments': Decimal(str(item.get('payments', 0.0))),
                'scholarships': Decimal(str(item.get('scholarships', 0.0)))
            }
            for item in summaries
        }


class StudentTransaction(models.Model):
    """
    Represents a financial transaction for a student account.
    Tracks debits (charges) and credits (payments, scholarships, refunds).
    """
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    student = models.ForeignKey(
        'cis.Student',
        on_delete=models.CASCADE
    )

    TRANSACTION_TYPES = [
        ('debit', 'Debit'),
        ('credit', 'Credit')
    ]

    DEBIT_TRANSACTION_TYPES = [
        ('class_charge', 'Class Charge'),
        ('school_charge', 'School Charge'),
        ('check_return_fee', 'Returned Check Fee'),
        ('other', 'Other')
    ]

    SCHOLARSHIP_TYPES = [
        ('1', 'Tuition Assistance'),
        ('2', 'Tuition Assistance - Direct Billed'),
        ('3', 'Tuition Remission')
    ]

    REFUND_TYPES = [
        ('R1', 'Refund')
    ]

    PAYMENT_TYPES = [
        ('check', 'By Check'),
        ('cc', 'By CC'),
        ('school_pay', 'By School'),
    ]

    t_type = models.CharField(
        choices=TRANSACTION_TYPES,
        blank=True,
        max_length=10,
        default='debit'
    )

    term = models.ForeignKey(
        'cis.Term',
        on_delete=models.PROTECT
    )

    amount = models.FloatField(default=0.0)

    # This can be user friendly type like Charge, Payment, Financial Assistance
    label = models.CharField(max_length=50, blank=True)

    # More detailed description like Tuition for ACC 101
    description = models.CharField(
        max_length=500, blank=True, null=True
    )

    created_on = models.DateTimeField(
        default=timezone.now
    )

    created_by = models.ForeignKey(
        'cis.CustomUser',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    meta = JSONField(
        blank=True, null=True
    )

    objects = StudentTransactionManager()

    @property
    def format_amount(self):
        try:
            if self.amount < 0:
                return "(${:0,.2f})".format(abs(self.amount))
            return "${:0,.2f}".format(self.amount)
        except (ValueError, TypeError):
            return self.amount

    @property
    def registration(self):
        from cis.models.section import StudentRegistration
        if self.meta and self.meta.get('registration'):
            registration = StudentRegistration.objects.filter(
                id=self.meta.get('registration')
            ).first()
            if registration:
                return f"{registration.class_section.course} / {registration.class_section.class_number} / {registration.sexy_status}"
        return '-'

    @property
    def is_refund(self):
        return self.t_type == 'credit' and self.label in dict(self.REFUND_TYPES)

    @property
    def sexy_description(self):
        description = self.description or ''
        if description:
            description += " "

        if self.is_refund:
            description += 'Refund '

        if self.meta:
            if self.meta.get('check_number'):
                description += f"Check # {self.meta.get('check_number')}<br>"
            if self.meta.get('check_date'):
                description += f"Check Date - {self.meta.get('check_date')}<br>"

        return description

    @property
    def check_date(self):
        return self.meta.get('check_date') if self.meta else None

    @property
    def check_number(self):
        return self.meta.get('check_number') if self.meta else None

    def send_payment_confirmation(self):
        from cis.settings.registration_charges import registration_charges

        email_settings = registration_charges.from_db()
        email_template = Template(email_settings.get('payment_received_email', 'change me'))

        context = Context({
            'student_first_name': self.student.user.first_name,
            'student_last_name': self.student.user.last_name,
            'payment_date': self.created_on.strftime('%m/%d/%Y'),
            'payment_amount': self.amount
        })
        text_body = email_template.render(context)

        to = [self.student.user.email]
        try:
            validate_email(self.student.parent_email)
            to.append(self.student.parent_email)
        except Exception:
            pass

        if getattr(settings, 'DEBUG', False):
            debug_email = getattr(settings, 'DEBUG_EMAIL_RECIPIENT', None)
            if debug_email:
                to = [debug_email]

        subject = email_settings.get('payment_received_email_subject', 'change me')

        template = get_template('cis/email.html')
        html_body = template.render({
            'message': text_body
        })

        send_html_mail(
            subject,
            text_body,
            html_body,
            settings.DEFAULT_FROM_EMAIL,
            to
        )

    @property
    def sexy_label(self):
        if self.t_type == 'debit':
            return dict(self.DEBIT_TRANSACTION_TYPES).get(self.label)
        return (
            dict(self.REFUND_TYPES).get(self.label) or
            dict(self.SCHOLARSHIP_TYPES).get(self.label) or
            dict(self.PAYMENT_TYPES).get(self.label)
        )

    @property
    def ce_url(self):
        if self.t_type == 'debit':
            return reverse_lazy(
                'student_transactions:edit_debit',
                kwargs={
                    'student_id': self.student.id,
                    'transaction_id': self.id
                }
            )
        else:
            if self.label == '1':
                return reverse_lazy(
                    'student_transactions:edit_scholarship',
                    kwargs={
                        'student_id': self.student.id,
                        'transaction_id': self.id
                    }
                )
            return reverse_lazy(
                'student_transactions:edit_payment',
                kwargs={
                    'student_id': self.student.id,
                    'transaction_id': self.id
                }
            )
