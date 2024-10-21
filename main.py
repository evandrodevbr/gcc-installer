import sys
import os
import subprocess
import urllib.request
import importlib
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import logging
from tqdm import tqdm
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil
import winreg
import queue
from datetime import datetime
import platform
import webbrowser
import win32gui
import win32con
import threading
import functools


def download_file(url, filename):
    with urllib.request.urlopen(url) as response, open(filename, 'wb') as out_file:
        data = response.read()
        out_file.write(data)


def install_pip():
    print("Pip não encontrado. Instalando pip...")
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_filename = "get-pip.py"
    
    try:
        download_file(get_pip_url, get_pip_filename)
        subprocess.check_call([sys.executable, get_pip_filename])
        os.remove(get_pip_filename)
        print("Pip instalado com sucesso.")
    except Exception as e:
        print(f"Erro ao instalar pip: {e}")
        sys.exit(1)


def check_pip():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
    except subprocess.CalledProcessError:
        install_pip()


def install_and_import(package):
    try:
        if package == 'pywin32':
            import win32api
        else:
            importlib.import_module(package)
    except ImportError:
        print(f"{package} não encontrado. Instalando...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            if package == 'pywin32':
                import win32api
            else:
                globals()[package] = importlib.import_module(package)
        except subprocess.CalledProcessError:
            print(f"Erro ao instalar {package}. Por favor, instale manualmente.")
            sys.exit(1)
        except ImportError:
            if package == 'pywin32':
                print("pywin32 instalado, mas não pode ser importado diretamente. Isso é normal.")
            else:
                print(f"Erro: Não foi possível importar {package} após a instalação.")
                sys.exit(1)


def verify_installation(module_name):
    try:
        importlib.import_module(module_name)
        print(f"{module_name} instalado com sucesso.")
    except ImportError:
        print(f"Erro: {module_name} não foi instalado corretamente.")
        sys.exit(1)


print("Verificando se o pip está instalado...")
check_pip()

print("Instalando e verificando dependências...")
dependencies = [
    'requests',
    'tqdm',
    'watchdog',
    'pywin32'
]

for dep in dependencies:
    install_and_import(dep)

# Verificar explicitamente os módulos do pywin32
pywin32_modules = ['win32gui', 'win32con']
for module in pywin32_modules:
    try:
        globals()[module] = importlib.import_module(module)
        print(f"{module} importado com sucesso.")
    except ImportError:
        print(f"Erro: Não foi possível importar {module}. Verifique se pywin32 está instalado corretamente.")
        sys.exit(1)

print("Todas as dependências foram instaladas e verificadas com sucesso.")


class MinGWDownloader:

    def __init__(self):
        self.github_api_url = "https://api.github.com/repos/niXman/mingw-builds-binaries/releases"
        self.download_folder = "mingw_downloads"
        self.log_queue = queue.Queue()
        self.cached_versions = []
        self.setup_logging()
        self.setup_gui()
        self.download_folder = os.path.dirname(os.path.abspath(sys.executable))
        self.setup_folder_monitoring()
        self.system_info = self.get_system_info()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='mingw_downloader.log',
            filemode='w'
        )
        self.logger = logging.getLogger(__name__)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("evandro.dev.br - G++ Compiler Installer")
        self.root.geometry("800x600")
        self.root.iconbitmap('evandro.ico')

        self.frame = ttk.Frame(self.root, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.setup_search_bar()
        self.setup_treeview()
        self.setup_buttons()
        self.setup_dev_info()
        self.setup_log_and_progress()

    def setup_search_bar(self):
        self.search_frame = ttk.Frame(self.frame)
        self.search_frame.pack(fill=tk.X, pady=(0, 10))

        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(self.search_frame, textvariable=self.filter_var)
        self.filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.filter_entry.bind('<KeyRelease>', self.filter_treeview)

    def setup_treeview(self):
        columns = ("Version", "File", "Status", "Date")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.treeview_sort_column(self.tree, _col, False))
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.tag_configure('hidden', foreground='gray')

    def setup_buttons(self):
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        buttons = [
            ("Download Selected", self.download_selected),
            ("Install MinGW", self.install_mingw),
            ("Download and Install", self.download_and_install),
            ("Remove Downloaded Version", self.remove_downloaded),
            ("Refresh Versions", self.fetch_versions),
            ("Add to PATH", self.add_mingw_to_path)
        ]

        for text, command in buttons:
            ttk.Button(self.button_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)

    def setup_dev_info(self):
        self.dev_frame = ttk.Frame(self.frame)
        self.dev_frame.pack(fill=tk.X, pady=10)

        ttk.Label(self.dev_frame, text="Developed by Evandro Fonseca Junior", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(self.dev_frame, text="Portfolio", command=lambda: webbrowser.open("https://evandro.dev.br/")).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.dev_frame, text="GitHub", command=lambda: webbrowser.open("https://github.com/evandrodevbr")).pack(side=tk.LEFT)

    def setup_log_and_progress(self):
        self.log_text = scrolledtext.ScrolledText(self.frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

        self.progress_bar = ttk.Progressbar(self.frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress_bar.pack(pady=5)

    def setup_folder_monitoring(self):
        os.makedirs(self.download_folder, exist_ok=True)
        event_handler = DownloadFolderHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.download_folder, recursive=False)
        self.observer.start()

    def process_log_queue(self):
        while True:
            try:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + '\n')
                self.log_text.see(tk.END)
                self.log_queue.task_done()
            except queue.Empty:
                break
        self.root.after(100, self.process_log_queue)

    def log_message(self, message):
        self.logger.info(message)
        self.log_queue.put(message)

    def get_system_info(self):
        arch = 'x86_64' if platform.machine().endswith('64') else 'i686'
        return {
            'arch': arch,
            'bits': '64' if arch == 'x86_64' else '32',
            'os': 'win32'
        }

    @functools.lru_cache(maxsize=None)
    def fetch_versions(self):
        self.log_message("Fetching available versions")
        self.tree.delete(*self.tree.get_children())
        try:
            response = requests.get(self.github_api_url)
            response.raise_for_status()
            releases = response.json()

            self.cached_versions = []
            for release in releases:
                version = release['tag_name']
                for asset in release['assets']:
                    if asset['name'].endswith('.7z'):
                        filename = asset['name']
                        date = datetime.strptime(asset['updated_at'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
                        status = "Downloaded" if self.is_downloaded(filename) else "Not Downloaded"
                        download_url = asset['browser_download_url']
                        self.cached_versions.append((version, filename, status, date, download_url))
                        self.tree.insert("", "end", values=(version, filename, status, date))

            self.log_message(f"Fetched {len(self.cached_versions)} versions")
            self.recommend_version()
            self.update_recommendation_highlight()
        except Exception as e:
            self.log_message(f"Error fetching versions: {str(e)}")
            messagebox.showerror("Error", f"Failed to fetch versions: {str(e)}")

    def recommend_version(self):
        for item in self.tree.get_children():
            filename = self.tree.item(item)['values'][1]
            if self.is_compatible_version(filename):
                self.tree.item(item, tags=('recommended',))
        self.tree.tag_configure('recommended', background='light green')
        messagebox.showinfo("Recommendation", f"Versions compatible with your {self.system_info['bits']}-bit {self.system_info['arch']} system are highlighted in light green.")

    def is_compatible_version(self, filename):
        parts = filename.split('-')
        if len(parts) < 7:
            return False
        
        arch, gcc_version, build_type, thread_model, exception_model, crt, revision = parts[:7]

        return (
            arch == self.system_info['arch'] and
            ((self.system_info['bits'] == '64' and exception_model == 'seh') or
             (self.system_info['bits'] == '32' and exception_model == 'dwarf')) and
            crt == 'ucrt' and
            thread_model == 'posix'
        )

    def is_downloaded(self, filename):
        return os.path.exists(os.path.join(self.download_folder, filename))

    def download_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a version to download")
            return

        version, filename, _, _ = self.tree.item(selected[0])['values']
        download_url = next((v[4] for v in self.cached_versions if v[0] == version and v[1] == filename), None)

        if not download_url:
            messagebox.showerror("Error", "Failed to find download URL")
            return

        threading.Thread(target=self._download_file, args=(filename, download_url)).start()

    def _download_file(self, filename, download_url):
        try:
            if self.is_downloaded(filename):
                self.log_message(f"File {filename} is already downloaded")
                messagebox.showinfo("Info", f"File {filename} is already downloaded")
                return

            self.log_message(f"Starting download of {filename}")
            file_path = os.path.join(self.download_folder, filename)

            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                block_size = 8192
                with open(file_path, 'wb') as f, tqdm(
                    desc=filename,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as progress_bar:
                    for chunk in r.iter_content(chunk_size=block_size):
                        size = f.write(chunk)
                        progress_bar.update(size)
                        self.root.after(0, self._update_progress, (progress_bar.n / total_size) * 100)

            self.log_message(f"Download complete: {file_path}")
            self.log_message(f"File size: {os.path.getsize(file_path)} bytes")
            messagebox.showinfo("Success", f"Successfully downloaded {filename}")
            self.root.after(0, self.update_file_status, filename, "Downloaded")
        except Exception as e:
            self.log_message(f"Error downloading {filename}: {str(e)}")
            messagebox.showerror("Error", f"Failed to download {filename}: {str(e)}")
        finally:
            self.root.after(0, self._reset_progress)

    def _install_mingw(self, version, filename):
        source_file_path = os.path.join(self.download_folder, filename)
        target_dir = r"C:\mingw64"
        temp_dir = r"C:\mingw_temp"

        try:
            self.log_message(f"Starting installation of MinGW {version}")
            self.log_message(f"Verifying file: {source_file_path}")
            if not os.path.exists(source_file_path):
                raise FileNotFoundError(f"Downloaded file not found: {source_file_path}")

            if not filename.endswith('.7z'):
                raise ValueError("The downloaded file is not in .7z format")

            # Move the .7z file to C: drive
            c_drive_file_path = os.path.join(r"C:", filename)
            shutil.copy(source_file_path, c_drive_file_path)
            self.log_message(f"Copied {filename} to C: drive")

            self.clean_temp_directory(temp_dir)
            self.log_message(f"Extracting to temporary directory: {temp_dir}")

            seven_zip_path = r"C:\Program Files\7-Zip\7z.exe"
            if not os.path.exists(seven_zip_path):
                raise FileNotFoundError("7-Zip is not installed or not found in the default location")

            extract_command = [seven_zip_path, "x", c_drive_file_path, f"-o{temp_dir}", "-y"]
            result = subprocess.run(extract_command, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Error extracting file: {result.stderr}")

            self.log_message("Extraction complete")

            self.log_message(f"Moving files to {target_dir}")

            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
                self.log_message(f"Removed existing directory: {target_dir}")

            extracted_dir = os.path.join(temp_dir, os.listdir(temp_dir)[0])
            shutil.move(extracted_dir, target_dir)
            self.log_message(f"MinGW installed to {target_dir}")

            # Remove the .7z file from C: drive
            os.remove(c_drive_file_path)
            self.log_message(f"Removed {filename} from C: drive")

            self.test_installation()
            self.rename_mingw32_make()

            self.log_message("Installation complete. You may need to add MinGW to your system PATH.")
            messagebox.showinfo("Installation Complete", "MinGW has been successfully installed. You may need to add it to your system PATH.")
        except Exception as e:
            self.log_message(f"Error during installation: {str(e)}")
            self.log_message(f"File path: {c_drive_file_path}")
            self.log_message(f"File exists: {os.path.exists(c_drive_file_path)}")
            self.log_message(f"File size: {os.path.getsize(c_drive_file_path) if os.path.exists(c_drive_file_path) else 'N/A'}")
            self.log_message(f"Temp directory contents: {os.listdir(temp_dir) if os.path.exists(temp_dir) else 'N/A'}")
            messagebox.showerror("Error", f"Failed to install MinGW: {str(e)}")
        finally:
            self.clean_temp_directory(temp_dir)

    def is_downloaded(self, filename):
        return os.path.exists(os.path.join(self.download_folder, filename))

    def _update_progress(self, value):
        self.progress_bar['value'] = value
        self.root.update_idletasks()

    def _reset_progress(self):
        self.progress_bar['value'] = 0
        self.root.update_idletasks()

    def install_mingw(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a version to install")
            return

        version, filename, status, _ = self.tree.item(selected[0])['values']
        if status != "Downloaded":
            messagebox.showinfo("Info", "Please download the selected version first")
            return

        threading.Thread(target=self._install_mingw, args=(version, filename)).start()

    def add_mingw_to_path(self):
        mingw_bin_path = r"C:\mingw64\bin"
        if not os.path.exists(mingw_bin_path):
            messagebox.showerror("Error", "MinGW installation not found. Please install MinGW first.")
            return

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS)
            current_path, _ = winreg.QueryValueEx(key, "Path")
            if mingw_bin_path not in current_path:
                new_path_value = f"{current_path};{mingw_bin_path}"
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_value)
                self.log_message(f"Added {mingw_bin_path} to PATH")
                win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
                self.log_message("Notified other processes of PATH change")
                messagebox.showinfo("Success", "MinGW has been added to your system PATH. You may need to restart your applications for the changes to take effect.")
            else:
                self.log_message(f"{mingw_bin_path} already in PATH")
                messagebox.showinfo("Info", "MinGW is already in your system PATH.")
            winreg.CloseKey(key)
        except Exception as e:
            self.log_message(f"Error updating PATH: {str(e)}")
            messagebox.showerror("Error", f"Failed to add MinGW to PATH: {str(e)}")

    def test_installation(self):
        try:
            self.log_message("Testing GCC installation...")
            gcc_version = subprocess.check_output(["gcc", "--version"], stderr=subprocess.STDOUT, text=True)
            self.log_message(f"GCC version: {gcc_version.split()[2]}")

            self.log_message("Testing G++ installation...")
            gpp_version = subprocess.check_output(["g++", "--version"], stderr=subprocess.STDOUT, text=True)
            self.log_message(f"G++ version: {gpp_version.split()[2]}")

            self.log_message("GCC and G++ are available")
            messagebox.showinfo("Installation Test", "GCC and G++ are successfully installed and available.")
        except subprocess.CalledProcessError:
            self.log_message("GCC or G++ not found. You may need to add MinGW to your system PATH.")
            messagebox.showwarning("Installation Test", "GCC or G++ not found. You may need to add MinGW to your system PATH.")

    def rename_mingw32_make(self):
        mingw32_make_path = r"C:\mingw64\bin\mingw32-make.exe"
        make_path = r"C:\mingw64\bin\make.exe"

        if os.path.exists(mingw32_make_path):
            try:
                os.rename(mingw32_make_path, make_path)
                self.log_message("Successfully renamed mingw32-make.exe to make.exe")
            except Exception as e:
                self.log_message(f"Error renaming mingw32-make.exe: {str(e)}")
        else:
            self.log_message("mingw32-make.exe not found")

    def remove_downloaded(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a version to remove")
            return

        version, filename, status, _ = self.tree.item(selected[0])['values']
        if status != "Downloaded":
            messagebox.showinfo("Info", "This version is not downloaded")
            return

        file_path = os.path.join(self.download_folder, filename)
        try:
            os.remove(file_path)
            self.log_message(f"Removed downloaded file: {file_path}")
            self.update_file_status(filename, "Not Downloaded")
            messagebox.showinfo("Success", f"Successfully removed {filename}")
        except Exception as e:
            self.log_message(f"Error removing file {filename}: {str(e)}")
            messagebox.showerror("Error", f"Failed to remove {filename}: {str(e)}")

    def download_and_install(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a version to download and install")
            return

        version, filename, status, _ = self.tree.item(selected[0])['values']

        if status != "Downloaded":
            self.download_selected()

        self.install_mingw()

    def filter_treeview(self, event=None):
        query = self.filter_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        for version, filename, status, date, _ in self.cached_versions:
            if query in version.lower() or query in filename.lower():
                self.tree.insert("", "end", values=(version, filename, status, date))
        self.update_recommendation_highlight()

    def update_recommendation_highlight(self):
        for item in self.tree.get_children():
            filename = self.tree.item(item)['values'][1]
            if self.is_compatible_version(filename):
                current_tags = list(self.tree.item(item)['tags'])
                if 'recommended' not in current_tags:
                    current_tags.append('recommended')
                self.tree.item(item, tags=current_tags)

    def treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def update_file_status(self, filename, status):
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][1] == filename:
                self.tree.item(item, values=(self.tree.item(item)['values'][0], filename, status, self.tree.item(item)['values'][3]))
                break

    def clean_temp_directory(self, temp_dir):
        self.log_message(f"Cleaning temporary directory: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

    def run(self):
        self.fetch_versions()
        self.root.after(100, self.process_log_queue)
        try:
            self.root.mainloop()
        finally:
            self.observer.stop()
            self.observer.join()


class DownloadFolderHandler(FileSystemEventHandler):

    def __init__(self, app):
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            self.app.root.after(0, self.app.update_file_status, filename, "Downloaded")

    def on_deleted(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            self.app.root.after(0, self.app.update_file_status, filename, "Not Downloaded")


if __name__ == "__main__":
    downloader = MinGWDownloader()
    downloader.run()

# TODO: Implement internationalization support for multi-language UI
# TODO: Adicionar suporte à internacionalização para interface em múltiplos idiomas
