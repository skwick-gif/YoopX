"""
Backup of the defensive WorkerThread implementation created during diagnostics work.
This file is a backup; the live worker module may be replaced with the legacy implementation next.
"""
import pathlib
import json

def _backup_marker():
    return {'backup_of': 'defensive_worker', 'note': 'keep this file for recovery'}

