from .version import is_newer, normalize_version

__all__ = ["UpdateDialog", "UpdateWorker", "is_newer", "normalize_version"]


def __getattr__(name):
    if name == "UpdateDialog":
        from .ui import UpdateDialog
        return UpdateDialog
    if name == "UpdateWorker":
        from .worker import UpdateWorker
        return UpdateWorker
    raise AttributeError(name)
