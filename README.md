# MinGW Downloader and Installer

## Important Note

Before using the auto-installer, please ensure that you have Python installed on your system. The auto-installer requires Python to run.

## About the Project

The MinGW Downloader and Installer is a Python-based graphical application designed to simplify the process of downloading, installing, and managing different versions of MinGW (Minimalist GNU for Windows). This tool is particularly useful for developers who need a GCC (GNU Compiler Collection) development environment on Windows platforms.

## Features

- List available MinGW versions from GitHub releases
- Download selected MinGW versions
- Install MinGW on the system
- Add MinGW to the system PATH
- Remove downloaded versions
- Filter and sort the version list
- Compatibility checking for system architecture

## Technologies Used

1. **Python**: The main programming language for this project. Python was chosen for its simplicity, readability, and extensive library support, making it ideal for rapid development of cross-platform applications.

2. **Tkinter**: Python's standard GUI (Graphical User Interface) library. Tkinter was selected for its ease of use and because it comes pre-installed with Python, eliminating the need for additional dependencies.

3. **Requests**: A popular HTTP library for Python. It's used in this project to make API calls to GitHub and download MinGW files. Requests was chosen for its intuitive design and robust feature set.

4. **Watchdog**: A Python API and shell utilities to monitor file system events. In this project, it's used to monitor changes in the download directory. Watchdog was selected for its cross-platform support and ease of integration.

5. **Subprocess**: A module that allows you to spawn new processes, connect to their input/output/error pipes, and obtain their return codes. It's used here to execute system commands, particularly for testing the MinGW installation.

6. **Threading**: Python's built-in threading module is used to implement asynchronous operations, improving the responsiveness of the GUI during long-running tasks like downloads and installations.

7. **Logging**: Python's logging module is used for tracking events that happen when the software runs. It was chosen to provide better debugging capabilities and to keep a record of the application's activities.

8. **Winreg**: A Windows-specific module used to access the Windows registry. It's utilized in this project to modify the system PATH, allowing for easy integration of MinGW into the user's development environment.

## Requirements

- Python 3.6 or higher
- 7-Zip installed in the default path (C:\Program Files\7-Zip\7z.exe)

## Installation

1. Clone the repository:

2. Navigate to the project directory:

3. Install the required dependencies:


## How to Use

1. Run the program: python mingw_downloader.py

2. **Download and Install MinGW**:
- In the application window, you'll see a list of available MinGW versions.
- Select a compatible version from the list (compatible versions are highlighted in green).
- Click on the "Download and Install" button.
- Wait for the download and installation process to complete.
- After completion, you will see a folder called "temp_extract" in the application's working directory.

3. **Add MinGW to PATH**:
- Once you see the "temp_extract" folder, click the "Add to PATH" button in the application.
- Confirm the addition when prompted.

4. **Verify the Installation**:
- Open a new command prompt (important to open a new one to refresh the environment variables).
- Type `gcc --version` and `g++ --version` to verify that MinGW was installed correctly and added to your PATH.

## Troubleshooting

- If you encounter any issues during the download or installation process, check the application's log file for more detailed error messages.
- Ensure that you have write permissions in the directory where you're running the application.
- If MinGW is not recognized after adding it to PATH, try restarting your computer to ensure all environment variables are updated.

## Contributing

Contributions to improve the MinGW Downloader and Installer are welcome. Please feel free to submit pull requests or create issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the MinGW-w64 project for providing the GCC port for Windows.
- This project uses the GitHub API to fetch MinGW releases.
