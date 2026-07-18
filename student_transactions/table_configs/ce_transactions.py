from ._base import build_table_config

COLUMN_HEADER_HTML = {
    'txn.select':        '<th></th>',
    'txn.created_on':    '<th data-data="created_on" data-name="created_on">Created On</th>',
    'txn.term':          '<th data-data="term.label" data-name="term.label" searchable="1">Term</th>',
    'txn.type':          '<th data-data="sexy_label" data-name="label" searchable="0">Type</th>',
    'txn.amount':        '<th data-data="format_amount" data-name="amount" searchable="0">Amount</th>',
    'txn.description':   '<th data-data="description" data-name="description" searchable="1">Description</th>',
    'txn.student':       '<th data-data="student.user.last_name" data-name="student.user.last_name" searchable="1">Student</th>',
    'txn.student_id':    '<th data-data="student.user.psid" data-name="student.user.psid" searchable="1">Student ID</th>',
    'txn.highschool':    '<th data-data="student.highschool.name" data-name="student.highschool.name" searchable="1">High School</th>',
    'txn.actions':       '<th data-data="id" data-name="id"><span class="sr-only">Actions</span></th>',
}

COLUMN_FOOTER_HTML = {
    'txn.term':        '<th>Term</th>',
    'txn.amount':      '<th>Amount</th>',
    'txn.description': '<th>Description</th>',
    'txn.student':     '<th>Student Last Name</th>',
    'txn.student_id':  '<th>Student ID</th>',
    'txn.highschool':  '<th>High School</th>',
}

_PROFILES = {
    'ce_index': {
        'table_id':      'transactions_all',
        'columns':       ['txn.select', 'txn.created_on', 'txn.term', 'txn.type',
                          'txn.amount', 'txn.description', 'txn.student',
                          'txn.student_id', 'txn.highschool', 'txn.actions'],
        'select_style':  'multi',
        'default_order': [1, 'desc'],
        'footer_search': True,
        'action_scope':  'bulk',
    },
}


def build_config(*, variant, api_url, summary_api_url='', bulk_actions=None,
                 bulk_actions_url=None):
    p = _PROFILES[variant]
    return build_table_config(
        profile=p,
        header_html=COLUMN_HEADER_HTML,
        footer_html=COLUMN_FOOTER_HTML,
        partial_template='transactions/_ce_table.html',
        include_bulk_actions=True,
        bulk_actions=bulk_actions,
        bulk_actions_url=bulk_actions_url,
        opts={
            'apiUrl':        api_url,
            'summaryApiUrl': summary_api_url,
            'columns':       p['columns'],
            'selectStyle':   p.get('select_style'),
            'defaultOrder':  p.get('default_order'),
        },
    )
