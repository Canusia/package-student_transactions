"""Transactions sidebar item (cis.menu_registry); the 50 of ce `students`.

On a cis without the registry nothing registers.
"""
try:
    from cis.menu_registry import menu
except ImportError:   # cis without the registry: the menu migrations still apply
    menu = None

if menu is not None:
    menu.register('ce', 'transactions', 'Transactions',
                  url='student_transactions:index', parent='students', order=50)
