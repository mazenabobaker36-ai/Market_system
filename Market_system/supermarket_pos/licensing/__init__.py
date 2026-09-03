from .manager import LicenseManager, LicenseState

__all__ = ["ActivationDialog", "LicenseCheckWorker", "LicenseLockOverlay", "LicenseManager", "LicenseState", "NetworkManager"]


def __getattr__(name):
    if name in {"ActivationDialog", "LicenseLockOverlay"}:
        from .ui import ActivationDialog, LicenseLockOverlay
        return {"ActivationDialog": ActivationDialog, "LicenseLockOverlay": LicenseLockOverlay}[name]
    if name == "LicenseCheckWorker":
        from .worker import LicenseCheckWorker
        return LicenseCheckWorker
    if name == "NetworkManager":
        from .network import NetworkManager
        return NetworkManager
    raise AttributeError(name)
