from django import forms
from django.core.exceptions import ValidationError

from cis.models.term import Term
from cis.models.student import Student
from cis.utils import active_term as get_active_term

from .models import StudentTransaction


class BaseTransactionForm(forms.Form):
    """Base form class for all transaction types with common fields and logic."""

    student = forms.ModelChoiceField(
        queryset=None,
        required=True,
        widget=forms.HiddenInput()
    )

    transaction_id = forms.CharField(
        required=True,
        widget=forms.HiddenInput()
    )

    term = forms.ModelChoiceField(
        queryset=None,
        label='Term'
    )

    description = forms.CharField(
        required=False,
        max_length=500
    )

    # Subclasses should define these
    t_type = 'credit'  # Default transaction type
    label_choices = []

    def __init__(self, student_id, transaction_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set up term queryset
        self.fields['term'].queryset = Term.objects.all().order_by('-code')
        self.fields['term'].initial = get_active_term()

        # Set up student queryset
        self.student_instance = Student.objects.filter(pk=student_id).first()
        self.fields['student'].queryset = Student.objects.filter(pk=student_id)
        self.fields['student'].initial = self.student_instance

        # Set up transaction_id
        if not transaction_id or str(transaction_id) == '-1':
            self.fields['transaction_id'].initial = '-1'
            self.transaction_instance = None
        else:
            self.transaction_instance = StudentTransaction.objects.get(pk=transaction_id)
            self.fields['transaction_id'].initial = self.transaction_instance.id
            self._load_transaction_data()

    def _load_transaction_data(self):
        """Load existing transaction data into form fields. Override in subclasses for custom fields."""
        if self.transaction_instance:
            self.fields['term'].initial = self.transaction_instance.term
            self.fields['description'].initial = self.transaction_instance.description
            if 'label' in self.fields:
                self.fields['label'].initial = self.transaction_instance.label

    def _get_or_create_transaction(self):
        """Get existing transaction or create new one."""
        data = self.cleaned_data

        if data.get('transaction_id') == '-1':
            transaction = StudentTransaction()
            transaction.meta = {}
        else:
            transaction = StudentTransaction.objects.get(pk=data.get('transaction_id'))

        return transaction

    def _save_common_fields(self, transaction, request):
        """Save fields common to all transaction types."""
        data = self.cleaned_data

        transaction.term = data.get('term')
        transaction.t_type = self.t_type
        transaction.student = data.get('student')
        transaction.created_by = request.user
        transaction.description = data.get('description')

        if 'label' in data:
            transaction.label = data.get('label')

        return transaction


class StudentChargeForm(BaseTransactionForm):
    t_type = 'debit'

    label = forms.ChoiceField(
        choices=StudentTransaction.DEBIT_TRANSACTION_TYPES,
        help_text='',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'})
    )

    registration = forms.ChoiceField(
        choices=[],
        required=False
    )

    charge_amount = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'col-3'})
    )

    # Override to make description required
    description = forms.CharField(
        required=True,
        max_length=500
    )

    def __init__(self, student_id, transaction_id=None, *args, **kwargs):
        super().__init__(student_id, transaction_id, *args, **kwargs)

        self.fields['term'].label = 'Charge Term'

        # Set up registration choices
        if self.student_instance:
            registrations = self.student_instance.get_registrations().order_by(
                '-class_section__term__code',
                'class_section__course'
            )

            registration_choices = [
                (
                    str(reg.id),
                    f'{reg.class_section.course} / {reg.class_section.term} ({reg.status})'
                )
                for reg in registrations
            ]
            self.fields['registration'].choices = registration_choices

    def _load_transaction_data(self):
        super()._load_transaction_data()
        if self.transaction_instance:
            self.fields['charge_amount'].initial = self.transaction_instance.amount
            if self.transaction_instance.meta and self.transaction_instance.meta.get('registration'):
                self.fields['registration'].initial = self.transaction_instance.meta.get('registration')

    def save(self, request, commit=False):
        transaction = self._get_or_create_transaction()
        self._save_common_fields(transaction, request)

        data = self.cleaned_data
        transaction.amount = data.get('charge_amount')

        if data.get('registration'):
            transaction.meta['registration'] = data.get('registration')

        if commit:
            transaction.save()

        return transaction


class StudentScholarshipForm(BaseTransactionForm):
    t_type = 'credit'

    label = forms.ChoiceField(
        choices=StudentTransaction.SCHOLARSHIP_TYPES,
        help_text='',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'})
    )

    amount = forms.CharField(
        required=False,
        initial=0.0,
        label='Amount or Percentage',
        help_text='Eg: 100 or 60%. Adding amount or % will add a new TA to the student. If adding \'%\' it will calculated based off student balance.'
    )

    def __init__(self, student_id, transaction_id=None, *args, **kwargs):
        super().__init__(student_id, transaction_id, *args, **kwargs)

        self.fields['term'].label = 'TA Term'

        if self.student_instance:
            self.fields['amount'].help_text += f' Current Student Balance - ${self.student_instance.current_student_balance}'

    def _load_transaction_data(self):
        super()._load_transaction_data()
        if self.transaction_instance:
            self.fields['amount'].initial = self.transaction_instance.amount

    def clean_amount(self):
        amount = self.data.get('amount')

        if amount.endswith('%'):
            amount = amount.replace('%', '')

        try:
            float(amount)
        except ValueError:
            raise ValidationError('Please enter a valid amount or %')

        return self.data.get('amount')

    def save(self, request, commit=False):
        transaction = self._get_or_create_transaction()
        self._save_common_fields(transaction, request)

        data = self.cleaned_data
        student = data.get('student')
        amount = data.get('amount')

        if amount.endswith('%'):
            amount = float(amount.replace('%', ''))
            if data.get('label') == '2':
                amount = (student.current_school_balance * amount) / 100
            else:
                amount = (student.current_student_balance * amount) / 100
        else:
            amount = float(amount)

        transaction.amount = amount

        if commit:
            transaction.save()

        return transaction


class StudentRefundForm(BaseTransactionForm):
    t_type = 'credit'

    label = forms.ChoiceField(
        choices=StudentTransaction.REFUND_TYPES,
        help_text='',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'})
    )

    amount = forms.FloatField(
        help_text='',
        widget=forms.NumberInput(attrs={'class': 'col-3'})
    )

    def __init__(self, student_id, transaction_id=None, *args, **kwargs):
        super().__init__(student_id, transaction_id, *args, **kwargs)

        self.fields['term'].label = 'Refund Term'

    def _load_transaction_data(self):
        super()._load_transaction_data()
        if self.transaction_instance:
            self.fields['amount'].initial = abs(self.transaction_instance.amount)

    def save(self, request, commit=False):
        transaction = self._get_or_create_transaction()
        self._save_common_fields(transaction, request)

        data = self.cleaned_data
        # Make the amount negative for refunds
        transaction.amount = abs(data.get('amount')) * -1

        if commit:
            transaction.save()

        return transaction


class StudentPaymentForm(BaseTransactionForm):
    t_type = 'credit'

    action = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        initial='add'
    )

    label = forms.ChoiceField(
        choices=StudentTransaction.PAYMENT_TYPES,
        help_text='',
        widget=forms.Select(attrs={'class': 'col-md-4 col-sm-12'})
    )

    amount = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'col-3'})
    )

    check_number = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.TextInput(attrs={'class': 'col-3'})
    )

    check_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'col-4'})
    )

    def __init__(self, student_id, transaction_id=None, *args, **kwargs):
        super().__init__(student_id, transaction_id, *args, **kwargs)

        self.fields['term'].label = 'Payment Term'

        if self.student_instance:
            self.fields['amount'].help_text = (
                f"Student Balance: {self.student_instance.current_student_balance} <br> "
                f"School Balance: {self.student_instance.current_school_balance}"
            )

    def _load_transaction_data(self):
        super()._load_transaction_data()
        if self.transaction_instance:
            self.fields['amount'].initial = self.transaction_instance.amount

            if not self.transaction_instance.meta:
                self.transaction_instance.meta = {}

            if self.transaction_instance.meta.get('check_number'):
                self.fields['check_number'].initial = self.transaction_instance.meta.get('check_number')
            if self.transaction_instance.meta.get('check_date'):
                self.fields['check_date'].initial = self.transaction_instance.meta.get('check_date')

    def save(self, request, commit=False):
        data = self.cleaned_data

        # Handle delete action
        if data.get('transaction_id') != '-1' and data.get('action') == 'delete':
            transaction = StudentTransaction.objects.get(pk=data.get('transaction_id'))
            transaction.student.add_note(
                createdby=request.user,
                note=f'Deleting payment of {transaction.amount}'
            )
            transaction.delete()
            return transaction

        transaction = self._get_or_create_transaction()
        self._save_common_fields(transaction, request)

        transaction.amount = data.get('amount')

        if all([data.get('check_number'), data.get('check_date')]):
            transaction.meta['check_number'] = data.get('check_number')
            transaction.meta['check_date'] = data.get('check_date').strftime("%m/%d/%Y")

        if commit:
            transaction.save()

        return transaction
