import threading
import logging

log = logging.getLogger("kairo-sidecar.clipboard_mutex")

# Global reentrant lock to serialize all clipboard write + paste actions
CLIPBOARD_LOCK = threading.RLock()
