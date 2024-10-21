import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import os
import logging
from tqdm import tqdm
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
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


class MinGWDownloader:

    def __init__(self):
        self.github_api_url = "https://api.github.com/repos/niXman/mingw-builds-binaries/releases"
        self.download_folder = "mingw_downloads"
        self.log_queue = queue.Queue()
        self.cached_versions = []
        self.setup_logging()
        self.setup_gui()
        self.setup_folder_monitoring()
        self.system_info = self.get_system_info()

    def setup_logging(self):
        # Configuração do sistema de logging
        # Logging system configuration
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
        # Configuração da interface gráfica do usuário
        # Graphical User Interface setup
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
        # Configuração da barra de pesquisa
        # Search bar setup
        self.search_frame = ttk.Frame(self.frame)
        self.search_frame.pack(fill=tk.X, pady=(0, 10))

        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(self.search_frame, textvariable=self.filter_var)
        self.filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.filter_entry.bind('<KeyRelease>', self.filter_treeview)

    def setup_treeview(self):
        # Configuração da visualização em árvore
        # Treeview setup
        columns = ("Version", "File", "Status", "Date")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.treeview_sort_column(self.tree, _col, False))
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.tag_configure('hidden', foreground='gray')

    def setup_buttons(self):
        # Configuração dos botões
        # Buttons setup
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
        # Configuração das informações do desenvolvedor
        # Developer info setup
        self.dev_frame = ttk.Frame(self.frame)
        self.dev_frame.pack(fill=tk.X, pady=10)

        ttk.Label(self.dev_frame, text="Developed by Evandro Fonseca Junior", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(self.dev_frame, text="Portfolio", command=lambda: webbrowser.open("https://evandro.dev.br/")).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.dev_frame, text="GitHub", command=lambda: webbrowser.open("https://github.com/evandrodevbr")).pack(side=tk.LEFT)

    def setup_log_and_progress(self):
        # Configuração do log e barra de progresso
        # Log and progress bar setup
        self.log_text = scrolledtext.ScrolledText(self.frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)

        self.progress_bar = ttk.Progressbar(self.frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress_bar.pack(pady=5)

    def setup_folder_monitoring(self):
        # Configuração do monitoramento de pasta
        # Folder monitoring setup
        os.makedirs(self.download_folder, exist_ok=True)
        event_handler = DownloadFolderHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.download_folder, recursive=False)
        self.observer.start()

    def process_log_queue(self):
        # Processamento da fila de logs
        # Log queue processing
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
        # Registro de mensagens de log
        # Logging messages
        self.logger.info(message)
        self.log_queue.put(message)

    def get_system_info(self):
        # Obtenção de informações do sistema
        # Getting system information
        arch = 'x86_64' if platform.machine().endswith('64') else 'i686'
        return {
            'arch': arch,
            'bits': '64' if arch == 'x86_64' else '32',
            'os': 'win32'
        }

    @functools.lru_cache(maxsize=None)
    def fetch_versions(self):
        # Busca de versões disponíveis (com cache)
        # Fetching available versions (with caching)
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
        # Recomendação de versão compatível
        # Recommending compatible version
        for item in self.tree.get_children():
            filename = self.tree.item(item)['values'][1]
            if self.is_compatible_version(filename):
                self.tree.item(item, tags=('recommended',))
        self.tree.tag_configure('recommended', background='light green')
        messagebox.showinfo("Recommendation", f"Versions compatible with your {self.system_info['bits']}-bit {self.system_info['arch']} system are highlighted in light green.")

    def is_compatible_version(self, filename):
        # Verificação de compatibilidade da versão
        # Checking version compatibility
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
        # Verificação se o arquivo já foi baixado
        # Checking if the file is already downloaded
        return os.path.exists(os.path.join(self.download_folder, filename))

    def download_selected(self):
        # Download da versão selecionada
        # Downloading the selected version
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
        # Função interna para download de arquivo
        # Internal function for file download
        try:
            if self.is_downloaded(filename):
                self.log_message(f"File {filename} is already downloaded")
                messagebox.showinfo("Info", f"File {filename} is already downloaded")
                return

            self.log_message(f"Starting download of {filename}")
            os.makedirs(self.download_folder, exist_ok=True)
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

    def _update_progress(self, value):
        # Atualização da barra de progresso
        # Updating progress bar
        self.progress_bar['value'] = value
        self.root.update_idletasks()

    def _reset_progress(self):
        # Reinicialização da barra de progresso
        # Resetting progress bar
        self.progress_bar['value'] = 0
        self.root.update_idletasks()

    def install_mingw(self):
        # Instalação do MinGW
        # Installing MinGW
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a version to install")
            return

        version, filename, status, _ = self.tree.item(selected[0])['values']
        if status != "Downloaded":
            messagebox.showinfo("Info", "Please download the selected version first")
            return

        threading.Thread(target=self._install_mingw, args=(version, filename)).start()

    def _install_mingw(self, version, filename):
        # Função interna para instalação do MinGW
        # Internal function for MinGW installation
        file_path = os.path.join(self.download_folder, filename)
        target_dir = r"C:\mingw64"

        if os.path.exists(target_dir):
            response = messagebox.askyesno("Warning", f"The directory {target_dir} already exists. Do you want to overwrite it?")
            if not response:
                self.log_message("Installation cancelled by user")
                return
            self.log_message(f"Removing existing directory: {target_dir}")
            shutil.rmtree(target_dir, ignore_errors=True)

        try:
            self.log_message(f"Starting installation of MinGW {version}")
            self.log_message(f"Verifying file: {file_path}")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Downloaded file not found: {file_path}")

            if not filename.endswith('.7z'):
                raise ValueError("The downloaded file is not in .7z format")

            temp_dir = os.path.join(self.download_folder, "temp_extract")
            self.clean_temp_directory(temp_dir)
            self.log_message(f"Extracting to temporary  directory: {temp_dir}")

            seven_zip_path = r"C:\Program Files\7-Zip\7z.exe"
            if not os.path.exists(seven_zip_path):
                raise FileNotFoundError("7-Zip is not installed or not found in the default location")

            extract_command = [seven_zip_path, "x", file_path, f"-o{temp_dir}", "-y"]
            result = subprocess.run(extract_command, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Error extracting file: {result.stderr}")

            self.log_message("Extraction complete")

            self.log_message(f"Moving files to {target_dir}")

            try:
                extracted_dir = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                shutil.move(extracted_dir, target_dir)
                self.log_message(f"MinGW installed to {target_dir}")
            except Exception as e:
                self.log_message(f"Error moving files to {target_dir}: {str(e)}")
                self.log_message("Attempting to copy files instead...")
                shutil.copytree(extracted_dir, target_dir)
                self.log_message(f"MinGW copied to {target_dir}")

            self.test_installation()
            self.rename_mingw32_make()

            self.log_message("Installation complete. You may need to add MinGW to your system PATH.")
            messagebox.showinfo("Installation Complete", "MinGW has been successfully installed. You may need to add it to your system PATH.")
        except Exception as e:
            self.log_message(f"Error during installation: {str(e)}")
            self.log_message(f"File path: {file_path}")
            self.log_message(f"File exists: {os.path.exists(file_path)}")
            self.log_message(f"File size: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}")
            self.log_message(f"Temp directory contents: {os.listdir(temp_dir) if os.path.exists(temp_dir) else 'N/A'}")
        finally:
            self.clean_temp_directory(temp_dir)

    def add_mingw_to_path(self):
        # Adição do MinGW ao PATH do sistema
        # Adding MinGW to system PATH
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
        # Teste da instalação
        # Testing the installation
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
        # Renomeação do mingw32-make para make
        # Renaming mingw32-make to make
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
        # Remoção da versão baixada
        # Removing downloaded version
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
        # Download e instalação combinados
        # Combined download and installation
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a version to download and install")
            return

        version, filename, status, _ = self.tree.item(selected[0])['values']

        if status != "Downloaded":
            self.download_selected()

        self.install_mingw()

    def filter_treeview(self, event=None):
        # Filtragem da visualização em árvore
        # Filtering the treeview
        query = self.filter_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        for version, filename, status, date, _ in self.cached_versions:
            if query in version.lower() or query in filename.lower():
                self.tree.insert("", "end", values=(version, filename, status, date))
        self.update_recommendation_highlight()

    def update_recommendation_highlight(self):
        # Atualização do destaque de recomendação
        # Updating recommendation highlight
        for item in self.tree.get_children():
            filename = self.tree.item(item)['values'][1]
            if self.is_compatible_version(filename):
                current_tags = list(self.tree.item(item)['tags'])
                if 'recommended' not in current_tags:
                    current_tags.append('recommended')
                self.tree.item(item, tags=current_tags)

    def treeview_sort_column(self, tv, col, reverse):
        # Ordenação de colunas na visualização em árvore
        # Sorting columns in the treeview
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))

    def update_file_status(self, filename, status):
        # Atualização do status do arquivo
        # Updating file status
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][1] == filename:
                self.tree.item(item, values=(self.tree.item(item)['values'][0], filename, status, self.tree.item(item)['values'][3]))
                break

    def clean_temp_directory(self, temp_dir):
        # Limpeza do diretório temporário
        # Cleaning temporary directory
        self.log_message(f"Cleaning temporary directory: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

    def run(self):
        # Execução principal do aplicativo
        # Main application execution
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
