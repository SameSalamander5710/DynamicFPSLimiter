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
    # Import and run DFL_v4 directly
    import core.DFL_v4

def build_executable():
    PyInstaller.__main__.run([
        'src/core/DFL_v4.py',
        '--onedir',
        '--uac-admin',
        '--clean',
        '--noconfirm',
        '--noconsole',
        '--name', 'DynamicFPSLimiter',
        '--icon', 'src/assets/DynamicFPSLimiter.ico',
        '--version-file', 'src/metadata/version.txt',
        '--add-data', 'src/assets/DynamicFPSLimiter.ico:assets',
        '--add-data', 'src/assets/rtss.dll:assets',
        '--distpath', 'output/dist',
        '--workpath', 'output/build'
    ])

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