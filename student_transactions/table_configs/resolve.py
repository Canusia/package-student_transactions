import importlib
from django.conf import settings


def resolve_table_config(name, package_default):
    """Tenant override from settings.TABLE_CONFIGS_APP.services.<name>, else the
    package's built-in default module. Both expose build_config(...)."""
    try:
        return importlib.import_module(f'{settings.TABLE_CONFIGS_APP}.services.{name}')
    except ModuleNotFoundError:
        return importlib.import_module(package_default)
