from django.test import TestCase, override_settings

# Create your tests here.


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
