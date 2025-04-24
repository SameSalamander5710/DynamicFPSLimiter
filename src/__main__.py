import sys
import argparse
import PyInstaller.__main__

def run_app():
    # Import and run DFL_v4 directly
    import DFL_v4

def build_executable():
    PyInstaller.__main__.run([
        'src/DFL_v4.py',  # Changed from __main__.py to DFL_v4.py
        '--onedir',
        '--uac-admin',
        '--clean',
        '--noconfirm',
        '--noconsole',
        '--name', 'DynamicFPSLimiter',
        '--icon', 'src/DynamicFPSLimiter.ico',
        '--version-file', 'src/version.txt',
        '--add-data', 'src/DynamicFPSLimiter.ico:.',
        '--add-data', 'src/rtss-cli.exe:.',
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
        print("Running application...")
        run_app()