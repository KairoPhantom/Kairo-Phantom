"""
constants.py — Shared constants for the Kairo sidecar.

Keep all magic strings and configuration values here to prevent
divergence across multiple modules.
"""

# Backup file suffix used by all writers when creating a pre-edit backup.
# Previously diverged between .kairo_bak (word_master) and .kairo_backup (docx_writer).
KAIRO_BACKUP_SUFFIX = ".kairo_backup"

# Key used in writer response dicts to report the number of changes applied.
# Previously diverged between "applied" and "applied_count".
APPLIED_COUNT_KEY = "applied_count"
