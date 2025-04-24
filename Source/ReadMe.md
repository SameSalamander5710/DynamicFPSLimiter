# Dynamic FPS Limiter

## Installation

### Prerequisites
1. Ensure Python is installed on your system (Python 3)
2. Install pip if not already installed:
   ```cmd
   python -m ensurepip --default-pip
   ```

### Setting up Virtual Environment
1. Open a command prompt in the project directory
2. Create a virtual environment:
   ```cmd
   python -m venv venv
   ```
3. Activate the virtual environment:
   ```cmd
   venv\Scripts\activate
   ```
4. Install required packages:
   ```cmd
   pip install -r Source/requirements.txt
   ```

## Building the Executable

### Prerequisites
1. Install pyinstaller:
   ```cmd
   pip install pyinstaller
   ```

### Build Instructions
Run the following command from the main repository folder:

```cmd
pyinstaller Source\DFL_v4.py ^
    --onedir --uac-admin --clean --noconsole ^
    --name DynamicFPSLimiter ^
    --icon=Source\DynamicFPSLimiter.ico ^
    --version-file=Source\version.txt ^
    --add-data "Source\DynamicFPSLimiter.ico:." ^
    --add-data "Source\rtss-cli.exe:." ^
    --distpath Output\dist ^
    --workpath Output\build
```


