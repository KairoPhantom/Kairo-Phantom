"""
kairo_eye package
Exports: AppWatcher, FarscryService, ContextAssembler
"""

from sidecar.kairo_eye.farscry_service import FarscryService, ElementType
from sidecar.kairo_eye.app_watcher import AppWatcher, Domain, AppProfile
from sidecar.kairo_eye.context_assembler import ContextAssembler

__all__ = [
    "AppWatcher",
    "AppProfile",
    "Domain",
    "FarscryService",
    "ElementType",
    "ContextAssembler",
]
