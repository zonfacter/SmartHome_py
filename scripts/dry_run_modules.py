import os
import sys

# Sicherstellen, dass Projekt-Root im Pfad ist
project_root = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(project_root)  # root of repo
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Deaktiviere Sentry/externes Tracking während Dry-Run
os.environ.pop('SENTRY_DSN', None)

print('Dry-run: Auto-Discovery der Module starten...')

from module_manager import ModuleManager

m = ModuleManager()
try:
    m.auto_discover_modules()
    print('\nDry-run abgeschlossen. Gefundene Module:')
    for name in sorted(m.modules.keys()):
        info = m.modules[name]
        print(f" - {name}: status={info.status}")
except Exception as e:
    print('FEHLER während Auto-Discovery:', e)
    raise
