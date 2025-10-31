import sys
import os
import argparse
import PyInstaller.__main__
from ctypes import windll, byref, wintypes

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return windll.shell32.IsUserAnAdmin()
    except:
        return False

def relaunch_as_admin():
    """Relaunch the script with administrator privileges."""
    executable = sys.executable
    script = os.path.abspath(__file__)
    params = " ".join([f'"{arg}"' for arg in [script] + sys.argv[1:]])
    result = windll.shell32.ShellExecuteW(
        None, "runas", executable, params, None, 1
    )
    sys.exit()

def run_app():
    # Import and run DFL_v5 directly
    import core.DFL_v5

def build_executable():
    assets_dir = os.path.join(os.path.dirname(__file__), 'core', 'assets')
    add_data_args = []

    for root, _, files in os.walk(assets_dir):
        for fname in files:
            src_path = os.path.join(root, fname)
            rel_dir = os.path.relpath(root, assets_dir)
            if rel_dir == '.' or rel_dir == os.curdir:
                dest = 'assets'
            else:
                dest = os.path.join('assets', rel_dir)
            # Use os.pathsep so this works on Windows (PyInstaller expects ';' on Windows)
            add_data_args.extend(['--add-data', f'{src_path}{os.pathsep}{dest}'])

    base_args = [
        'src/core/DFL_v5.py',
        '--hidden-import=clr',
        '--hidden-import=clr_loader.netfx',
        '--hidden-import=pythonnet',
        '--hidden-import=clr_loader',
        '--onedir',
        '--uac-admin',
        '--clean',
        '--noconfirm',
        '--noconsole',
        '--name', 'DynamicFPSLimiter',
        '--icon', 'src/core/assets/DynamicFPSLimiter.ico',
        '--version-file', 'src/metadata/version.txt',
        '--distpath', 'output/dist',
        '--workpath', 'output/build',
    ]

    PyInstaller.__main__.run(base_args + add_data_args)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dynamic FPS Limiter')
    parser.add_argument('--build', action='store_true', help='Build executable')
    args = parser.parse_args()

    if args.build:
        print("Building executable...")
        build_executable()
    else:
        if not is_admin():
            relaunch_as_admin()
        run_app()