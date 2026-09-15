# Dynamic FPS Limiter

## Installation

### Prerequisites
1. Use 64-bit Windows and Python 3.12 (the version used by the build workflow).
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
   pip install -r src/requirements.txt
   ```

## Usage

### Running the Application
To run the application directly without building an executable:
1. Activate the virtual environment if not already activated:
   ```cmd
   venv\Scripts\activate
   ```
2. Run the application:
   ```cmd
   python src/__main__.py
   ```
   Note: The application will automatically request administrator privileges when needed.

### Building an Executable
To create a standalone executable:
1. Activate the virtual environment if not already activated:
   ```cmd
   venv\Scripts\activate
   ```
2. Build the executable (no admin rights required):
   ```cmd
   python src/__main__.py --build
   ```
3. The executable will be created in the `output/dist` directory.

### GitHub Actions Build
The **Build Windows** workflow builds the application on Windows after a push to
`main`. You can also start it manually from the repository's **Actions** tab.
It runs the regression tests, checks the bundled modules and assets, and uploads
`DynamicFPSLimiter-windows-x64.zip` as a build artifact. Extract the whole ZIP
before running `DynamicFPSLimiter.exe`.

### Notes
- **Administrator Privileges**: Only required when running the application, not when building.
- **Executable Location**: After building, find the executable in `output/dist`. It includes all dependencies.
