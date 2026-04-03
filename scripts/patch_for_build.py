"""
Patch Klarity source files for PyInstaller frozen binary mode.
Works on both Linux and Windows. Run this before building.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def patch_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        if old not in content:
            print(f"  WARNING: pattern not found in {filepath}: {old[:60]}...")
        content = content.replace(old, new, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Patched {filepath}")


def patch_klarity_py():
    filepath = os.path.join(BASE_DIR, 'src', 'klarity.py')
    print(f"Patching {filepath}...")

    replacements = [
        (
            """import os
import sys
import argparse""",
            """import os
import sys
import argparse

# Windows: hide console window when running in GUI mode (no cli/info args)
if sys.platform == 'win32' and getattr(sys, 'frozen', False):
    _cli_args = {'cli', 'info', 'download-models', '-h', '--help'}
    if not any(a in sys.argv for a in _cli_args):
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32')
            user32 = ctypes.WinDLL('user32')
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)
        except Exception:
            pass"""
        ),
        (
            """SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")
TEMP_DIR = os.path.join(SCRIPT_DIR, "tmp")""",
            """if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
    _internal = os.path.join(SCRIPT_DIR, '_internal')
    if os.path.isdir(_internal):
        SCRIPT_DIR = _internal
    MODELS_DIR = os.path.join(os.path.dirname(sys.executable), 'models')
    TEMP_DIR = os.path.join(os.path.dirname(sys.executable), 'tmp')
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    MODELS_DIR = os.path.join(SCRIPT_DIR, 'models')
    TEMP_DIR = os.path.join(SCRIPT_DIR, 'tmp')"""
        ),
    ]

    patch_file(filepath, replacements)


def patch_gui_py():
    filepath = os.path.join(BASE_DIR, 'src', 'gui.py')
    print(f"Patching {filepath}...")

    replacements = [
        (
            """THEME = {""",
            """# Frozen binary helpers
def _get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _get_klarity_exe():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.join(_get_app_dir(), 'klarity.py')

THEME = {"""
        ),
        (
            """                cwd=os.path.dirname(os.path.abspath(__file__))""",
            """                cwd=_get_app_dir()"""
        ),
        (
            """        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')""",
            """        logo_path = os.path.join(_get_app_dir(), 'logo.png')"""
        ),
        (
            """        def download():
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cmd = [sys.executable, os.path.join(script_dir, "klarity.py"), "download-models"]
            if mode == "lite":
                cmd.insert(3, "-lite")
            subprocess.run(cmd, cwd=script_dir)""",
            """        def download():
            exe = _get_klarity_exe()
            cmd = [exe, "download-models"]
            if mode == "lite":
                cmd.insert(1, "-lite")
            subprocess.run(cmd, cwd=_get_app_dir())"""
        ),
        (
            """        script_dir = os.path.dirname(os.path.abspath(__file__))
        klarity_path = os.path.join(script_dir, "klarity.py")""",
            """        klarity_exe = _get_klarity_exe()"""
        ),
        (
            """        cmd = [sys.executable, klarity_path, f"-{mode}", proc_mode, self.input_path, "--json-progress"]""",
            """        cmd = [klarity_exe, f"-{mode}", proc_mode, self.input_path, "--json-progress"]"""
        ),
    ]

    patch_file(filepath, replacements)


def main():
    print("=" * 50)
    print("Patching Klarity source for frozen binary build")
    print("=" * 50)
    patch_klarity_py()
    patch_gui_py()
    print("All patches applied successfully!")


if __name__ == '__main__':
    main()
