# gcc-installer

**GUI installer for MinGW-w64/GCC on Windows: lists the upstream GitHub builds, downloads the `.7z` packages, extracts them to `C:\mingw64` and can add the toolchain to your user PATH.**

![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

## About

Setting up GCC on Windows usually means finding the right MinGW-w64 build for your architecture, downloading a 100+ MB archive and extracting it by hand. This app does that in one window: it reads the release list of [`niXman/mingw-builds-binaries`](https://github.com/niXman/mingw-builds-binaries), marks the builds that match your machine (x86_64/i686, `seh`/`dwarf`, `ucrt`, `posix` thread model), downloads the one you pick and installs it into `C:\mingw64`. It also patches the user PATH so `gcc` and `g++` become available in new terminals, and renames `mingw32-make.exe` to `make.exe`.

It is a single-file tkinter application, meant for Windows developers who want a working `gcc`/`g++` in a few clicks.

## How it works

```
niXman/mingw-builds-binaries (GitHub Releases API)
              |
              |  JSON: tag_name + assets (*.7z)
              v
        tkinter GUI  (version table, filter, sort, recommended builds)
              |
              |  download (requests + tqdm, progress bar)
              v
   mingw_downloads\*.7z  ->  C:\mingw_temp  (extracted with 7-Zip)
                                   |
                                   v
                             C:\mingw64  ->  test: gcc --version / g++ --version
                                   |
                                   v
                    user PATH (HKCU\Environment) via winreg + WM_SETTINGCHANGE
```

- `fetch_versions()` reads the releases API and fills the table with every `.7z` asset (version, file, status, date).
- `_download_file()` streams the archive into `mingw_downloads` next to the application (the status column flips to `Downloaded`, also picked up by a `watchdog` observer on that folder).
- `_install_mingw()` copies the archive to `C:\`, extracts it with 7-Zip into `C:\mingw_temp`, moves the extracted folder to `C:\mingw64`, removes the archive from `C:\` and runs the `mingw32-make.exe` -> `make.exe` rename plus the `gcc`/`g++` check.
- `add_mingw_to_path()` appends `C:\mingw64\bin` to `HKCU\Environment\Path` and broadcasts `WM_SETTINGCHANGE`.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.7+ (no package layout, single `main.py`) |
| GUI | tkinter / ttk (stdlib) |
| HTTP | `requests` (GitHub API + downloads) |
| Progress | `tqdm` |
| File watching | `watchdog` (observer on the download folder) |
| Windows integration | `winreg` (stdlib), `pywin32` (`win32gui`/`win32con`) |
| Packaging | none, runs from source (works next to a PyInstaller executable too) |

## Requirements

- Windows (the app writes to `C:\mingw64`, uses the registry and `pywin32`)
- Python 3.7 or newer. The old README said 3.6, but `subprocess.run(..., text=True)` requires 3.7
- 7-Zip installed at the default location: `C:\Program Files\7-Zip\7z.exe` (hardcoded)
- Internet access to `api.github.com` and to the GitHub release assets
- ~1 GB of free space on `C:\` during installation (a 64-bit package is about 108 MB compressed)

## Quick start

```bash
git clone https://github.com/evandrodevbr/gcc-installer.git
cd gcc-installer
python -m pip install -r requirements.txt
python main.py
```

`main.py` can also install its own dependencies (`requests`, `tqdm`, `watchdog`, `pywin32`) on first run when `pip` is available, but `requirements.txt` is the reproducible path.

On Linux the script is importable but exits on start with an explicit warning, since the installer is Windows-only:

```
$ python3 main.py          # Linux
This installer is Windows-only: it installs MinGW-w64 into C:\mingw64, ...
exit code: 1
```

## Usage

| Button | What it does |
|---|---|
| Download Selected | Downloads the `.7z` of the selected row into `mingw_downloads\` (progress bar + log pane). |
| Install MinGW | Requires the row to be `Downloaded`. Extracts and installs to `C:\mingw64`, then runs the `gcc`/`g++` check. |
| Download and Install | Runs both steps in a single background thread. |
| Remove Downloaded Version | Deletes the archive from `mingw_downloads\`. |
| Refresh Versions | Fetches the release list from GitHub again. |
| Add to PATH | Appends `C:\mingw64\bin` to the user PATH (`HKCU\Environment`). Open a new terminal afterwards. |

The search box filters the table by version or file name, and the column headers sort it. Builds matching your architecture/exception model/CRT/thread model are highlighted in light green.

Installation steps performed on disk:

1. `mingw_downloads\<file>.7z` (download)
2. `C:\<file>.7z` (temporary copy)
3. `C:\mingw_temp\<extracted folder>` (7-Zip extraction)
4. `C:\mingw64` (existing folder is removed and replaced)
5. archive removed from `C:\`; `mingw32-make.exe` renamed to `make.exe`

## Tests and checks

There is no CI. The checks that exist are the ones you can run from the repository:

```bash
python -m py_compile main.py                     # syntax
ruff check main.py tests/                        # optional linter (ruff 0.6.9 used here)
python -m unittest discover -s tests -v          # 13 tests, stdlib only
SKIP_LIVE=1 python -m unittest discover -s tests -v   # skips the GitHub API test
```

`tests/test_core.py` covers the pure logic (build compatibility, download folder, the download-then-install flow, the Windows-only guard) and one live test that validates the GitHub releases API contract the GUI depends on. It needs `requests` installed.

## Current state and limitations

- **Windows-only**: the GUI, the PATH change (`winreg`/`pywin32`), the `C:\mingw64` target and the 7-Zip extraction cannot be exercised on Linux. The GUI flow has not been run end-to-end on Windows in this revision; only the logic that is platform independent is covered by tests.
- The 7-Zip path is hardcoded to `C:\Program Files\7-Zip\7z.exe`; a portable or non-default 7-Zip is not detected.
- Only `ucrt` + `posix` thread model builds are highlighted as recommended. Upstream also ships `mcf` thread model and `msvcrt` builds, which are valid choices but are not auto-recommended here.
- Releases up to about 12.2 have no `ucrt` (`seh`+`posix`) asset, so nothing is highlighted for them and you have to pick a build manually.
- Installing into `C:\mingw64` deletes an existing `C:\mingw64` directory without confirmation.
- Downloads are kept in `mingw_downloads\` next to the app (`mingw_downloader.log` holds the log); both are gitignored.
- Some tkinter dialogs are still opened from worker threads (original design); it works in practice but is not the thread-safe pattern.
- No packaged executable, no installer, no code signing.

## Project structure

```
.
├── main.py            application: GUI, download, install, PATH (single file)
├── evandro.ico        window icon used by the GUI
├── requirements.txt   runtime dependencies
├── tests/
│   └── test_core.py   unittest suite for the platform-independent logic
├── LICENSE            MIT
└── README.md
```

Directories created at runtime: `mingw_downloads/` (downloads) and `mingw_downloader.log`.

## Documentation

There are no extra docs: the application is a single file, `main.py`, and this README describes what it does. Code comments are in Portuguese in the older parts and English in the newer ones.

## License

MIT, see [`LICENSE`](LICENSE).
