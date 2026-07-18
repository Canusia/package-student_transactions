import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase, RequestFactory, override_settings

try:
    from django_login_history.models import post_login as _login_history_post_login
except Exception:  # pragma: no cover
    _login_history_post_login = None

# Create your tests here.


def _sfx():
    return uuid.uuid4().hex[:8]


class CeTransactionsTableConfigTest(TestCase):
    def test_build_config_shape(self):
        from student_transactions.student_transactions.table_configs import ce_transactions
        cfg = ce_transactions.build_config(variant='ce_index', api_url='/x?format=datatables')
        self.assertEqual(cfg['table_id'], 'transactions_all')
        self.assertEqual(len(cfg['column_headers']), 10)
        self.assertIn('opts_json', cfg)
        self.assertIn('bulk_actions', cfg)

    def test_resolve_falls_back_to_package_default(self):
        from student_transactions.student_transactions.table_configs.resolve import resolve_table_config
        pkg = 'student_transactions.student_transactions.table_configs.ce_transactions'
        with override_settings(TABLE_CONFIGS_APP='nonexistent_app'):
            mod = resolve_table_config('ce_transactions_table', pkg)
        self.assertTrue(hasattr(mod, 'build_config'))


User = get_user_model()


class DoBulkActionTests(TestCase):
    """Actions backend: package-owned ActionRegistry, row actions, do_bulk_action."""

    @classmethod
    def setUpClass(cls):
        if _login_history_post_login is not None:
            user_logged_in.disconnect(_login_history_post_login)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if _login_history_post_login is not None:
            user_logged_in.connect(_login_history_post_login)

    def setUp(self):
        from cis.models.term import AcademicYear, Term
        from cis.models.course import Campus, Cohort, Course
        from cis.models.section import ClassSection, StudentRegistration
        from cis.models.student import Student
        from django.conf import settings
        from .models import StudentTransaction

        self.StudentTransaction = StudentTransaction

        Group.objects.get_or_create(name='student')
        User.objects.get_or_create(username='cron', defaults={'email': 'cron@x.com'})

        self.ay = AcademicYear.objects.create(name=f'AY-{_sfx()}')
        self.term = Term.objects.create(
            academic_year=self.ay, code='FA', label=f'Fall-{_sfx()}')
        self.cohort = Cohort.objects.create(name=f'Co-{_sfx()}', designator='CO')
        self.campus_a = Campus.objects.create(
            name=f'A-{_sfx()}', code=f'{settings.CAMPUS_CODE_PREFIX}-{_sfx()}')
        self.campus_b = Campus.objects.create(
            name=f'B-{_sfx()}', code=f'{settings.CAMPUS_CODE_PREFIX}-{_sfx()}')
        self.course_a = Course.objects.create(
            catalog_number='101', title='A', cohort=self.cohort, campus=self.campus_a)
        self.course_b = Course.objects.create(
            catalog_number='102', title='B', cohort=self.cohort, campus=self.campus_b)
        self.sec_a = ClassSection.objects.create(
            class_number='1001', term=self.term, course=self.course_a)
        self.sec_b = ClassSection.objects.create(
            class_number='1002', term=self.term, course=self.course_b)

        self.txn_a = self._transaction(self.sec_a)
        self.txn_b = self._transaction(self.sec_b)

        self.ce = User.objects.create_user(
            username=f'ce_{_sfx()}', email=f'ce_{_sfx()}@x.com', password='x')
        self.ce.groups.add(Group.objects.get_or_create(name='ce')[0])
        self.ce.campus = {'process_campus': [str(self.campus_a.id)]}
        self.ce.save()

    def _transaction(self, section):
        from cis.models.section import StudentRegistration
        from cis.models.student import Student

        u = User.objects.create_user(
            username=f'stu_{_sfx()}', email=f'stu_{_sfx()}@x.com', password='x')
        student = Student.objects.create(user=u, account_verified=True)
        StudentRegistration.objects.create(
            student=student, class_section=section, status='applied',
            status_changed_on={'applied_on': '01/01/2024'})
        return self.StudentTransaction.objects.create(
            student=student, term=self.term, t_type='payment', amount=100)

    def test_delete_transactions_deletes_only_campus_accessible(self):
        from .views.ce import do_bulk_action

        req = RequestFactory().post('/ce/student_transactions/transactions/bulk-action/', {
            'action': 'delete_transactions',
            'ids[]': [str(self.txn_a.id), str(self.txn_b.id)],
        })
        req.user = self.ce

        resp = do_bulk_action(req)

        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.content)
        self.assertEqual(data['outcome'], 'call')
        self.assertEqual(data['fn'], 'onBulkActionComplete')

        self.assertFalse(
            self.StudentTransaction.objects.filter(pk=self.txn_a.id).exists())
        self.assertTrue(
            self.StudentTransaction.objects.filter(pk=self.txn_b.id).exists())

    def test_manage_payment_action_returns_open_outcome(self):
        from .actions import transaction_actions

        req = RequestFactory().post('/ce/student_transactions/transactions/bulk-action/', {
            'action': 'manage_payment',
            'student_id': str(self.txn_a.student.id),
        })
        req.user = self.ce

        resp = transaction_actions.dispatch(req, 'manage_payment')

        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.content)
        self.assertEqual(data['outcome'], 'open')
        self.assertIn('url', data)
        self.assertIn(str(self.txn_a.student.id), data['url'])

    def test_manage_payment_action_with_transaction_id_builds_edit_url(self):
        from .actions import transaction_actions

        req = RequestFactory().post('/ce/student_transactions/transactions/bulk-action/', {
            'action': 'manage_payment',
            'student_id': str(self.txn_a.student.id),
            'transaction_id': str(self.txn_a.id),
        })
        req.user = self.ce

        resp = transaction_actions.dispatch(req, 'manage_payment')

        import json
        data = json.loads(resp.content)
        self.assertEqual(data['outcome'], 'open')
        self.assertIn(str(self.txn_a.id), data['url'])

    def test_download_receipt_action_returns_open_outcome(self):
        from .actions import transaction_actions

        req = RequestFactory().post('/ce/student_transactions/transactions/bulk-action/', {
            'action': 'download_receipt',
            'student_id': str(self.txn_a.student.id),
        })
        req.user = self.ce

        resp = transaction_actions.dispatch(req, 'download_receipt')

        import json
        data = json.loads(resp.content)
        self.assertEqual(data['outcome'], 'open')
        self.assertIn(str(self.txn_a.student.id), data['url'])

    def test_unknown_action_slug_returns_alert_400(self):
        from .actions import transaction_actions

        req = RequestFactory().post('/ce/student_transactions/transactions/bulk-action/', {
            'action': 'nonexistent_action',
        })
        req.user = self.ce

        resp = transaction_actions.dispatch(req, 'nonexistent_action')

        self.assertEqual(resp.status_code, 400)
        import json
        data = json.loads(resp.content)
        self.assertEqual(data['outcome'], 'alert')

    def test_do_bulk_action_dispatches_row_action_slugs(self):
        from .views.ce import do_bulk_action

        req = RequestFactory().post('/ce/student_transactions/transactions/bulk-action/', {
            'action': 'manage_scholarship',
            'student_id': str(self.txn_a.student.id),
        })
        req.user = self.ce

        resp = do_bulk_action(req)

        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.content)
        self.assertEqual(data['outcome'], 'open')
