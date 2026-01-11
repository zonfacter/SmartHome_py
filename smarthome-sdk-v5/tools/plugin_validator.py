import json
import os
import sys

def validate_plugin(path):
    print(f"🔍 Validiere Plugin-Struktur in: {path}")
    
    # Check 1: Manifest
    manifest_path = os.path.join(path, "manifest.json")
    if not os.path.exists(manifest_path):
        print("❌ Fehler: manifest.json fehlt!")
        return False

    # Check 2: Main Code
    main_path = os.path.join(path, "main.py")
    if not os.path.exists(main_path):
        print("❌ Fehler: main.py fehlt!")
        return False

    # Check 3: Erbt von BasePlugin?
    with open(main_path, 'r') as f:
        content = f.read()
        if "BasePlugin" not in content:
            print("❌ Fehler: Plugin erbt nicht von BasePlugin!")
            return False

    print("✅ Validierung erfolgreich! Das Plugin ist bereit für den Import.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plugin_validator.py <plugin_folder>")
    else:
        validate_plugin(sys.argv[1])