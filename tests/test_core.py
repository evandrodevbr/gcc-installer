"""Testes da lógica pura do gcc-installer.

Rodam no Linux e no Windows, só com a biblioteca padrão (`unittest`):

    python -m unittest discover -s tests -v

O que NÃO é coberto: a janela tkinter, a cópia para C:\\mingw64, a edição do
PATH via winreg, a extração com 7-Zip e o download real do .7z (100+ MB).
Essas partes só existem no Windows e não são verificáveis no Linux.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402  (depende do sys.path ajustado acima)

ASSET_64 = 'x86_64-16.2.0-release-posix-seh-ucrt-rt_v14-rev1.7z'
SISTEMA_64 = {'arch': 'x86_64', 'bits': '64', 'os': 'win32'}
SISTEMA_32 = {'arch': 'i686', 'bits': '32', 'os': 'win32'}


def make_app(**attrs):
    """Instância sem passar pelo __init__ (que abre a GUI tkinter)."""
    app = main.MinGWDownloader.__new__(main.MinGWDownloader)
    app.cached_versions = []
    for key, value in attrs.items():
        setattr(app, key, value)
    return app


class CompatibilidadeTests(unittest.TestCase):
    """is_compatible_version() decide o que a GUI destaca como recomendado."""

    def test_build_64bits_ucrt_posix_e_compativel(self):
        app = make_app(system_info=SISTEMA_64)
        self.assertTrue(app.is_compatible_version(ASSET_64))

    def test_build_i686_nao_serve_para_sistema_64bits(self):
        app = make_app(system_info=SISTEMA_64)
        self.assertFalse(app.is_compatible_version('i686-16.2.0-release-posix-dwarf-ucrt-rt_v14-rev1.7z'))

    def test_build_msvcrt_nao_e_recomendado(self):
        app = make_app(system_info=SISTEMA_64)
        self.assertFalse(app.is_compatible_version('x86_64-16.2.0-release-posix-seh-msvcrt-rt_v14-rev1.7z'))

    def test_sistema_32bits_recomenda_dwarf(self):
        app = make_app(system_info=SISTEMA_32)
        self.assertTrue(app.is_compatible_version('i686-16.2.0-release-posix-dwarf-ucrt-rt_v14-rev1.7z'))

    def test_nome_fora_do_padrao_nao_quebra(self):
        app = make_app(system_info=SISTEMA_64)
        self.assertFalse(app.is_compatible_version('mingw.7z'))
        self.assertFalse(app.is_compatible_version(''))


class PastaDeDownloadTests(unittest.TestCase):

    def test_is_downloaded_olha_o_arquivo_na_pasta(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = make_app(download_folder=tmp)
            self.assertFalse(app.is_downloaded(ASSET_64))
            open(os.path.join(tmp, ASSET_64), 'wb').close()
            self.assertTrue(app.is_downloaded(ASSET_64))

    def test_find_download_url_acha_pela_versao_e_arquivo(self):
        app = make_app()
        app.cached_versions = [
            ('16.2.0-rt_v14-rev1', ASSET_64, 'Not Downloaded', '2026-08-16', 'https://example.invalid/a.7z'),
            ('15.2.0-rt_v13-rev1', 'x86_64-15.2.0-release-posix-seh-ucrt-rt_v13-rev1.7z',
             'Not Downloaded', '2025-08-10', 'https://example.invalid/b.7z'),
        ]
        self.assertEqual(app.find_download_url('16.2.0-rt_v14-rev1', ASSET_64), 'https://example.invalid/a.7z')
        self.assertEqual(
            app.find_download_url('15.2.0-rt_v13-rev1', 'x86_64-15.2.0-release-posix-seh-ucrt-rt_v13-rev1.7z'),
            'https://example.invalid/b.7z',
        )
        self.assertIsNone(app.find_download_url('16.2.0-rt_v14-rev1', 'nao-existe.7z'))


class DownloadEInstalacaoTests(unittest.TestCase):
    """Regressão: 'Download and Install' precisa instalar DEPOIS do download.

    Antes o clique disparava a thread de download e chamava install_mingw() na
    sequência; como o status na tabela ainda era 'Not Downloaded', o app
    respondia sempre com 'Please download the selected version first'.
    """

    def _app(self, ja_baixado, download_ok=True):
        app = make_app(system_info=SISTEMA_64, calls=[])
        app.is_downloaded = lambda filename: ja_baixado
        app._download_file = lambda filename, url: (
            app.calls.append(('download', filename)), download_ok
        )[1]
        app._install_mingw = lambda version, filename: app.calls.append(('install', version, filename))
        return app

    def test_baixa_e_depois_instala(self):
        app = self._app(ja_baixado=False)
        app._download_then_install('16.2.0-rt_v14-rev1', ASSET_64, 'https://example.invalid/a.7z')
        self.assertEqual([chamada[0] for chamada in app.calls], ['download', 'install'])

    def test_download_que_falha_nao_instala(self):
        app = self._app(ja_baixado=False, download_ok=False)
        app._download_then_install('16.2.0-rt_v14-rev1', ASSET_64, 'https://example.invalid/a.7z')
        self.assertEqual([chamada[0] for chamada in app.calls], ['download'])

    def test_arquivo_ja_baixado_vai_direto_para_a_instalacao(self):
        app = self._app(ja_baixado=True)
        app._download_then_install('16.2.0-rt_v14-rev1', ASSET_64, 'https://example.invalid/a.7z')
        self.assertEqual([chamada[0] for chamada in app.calls], ['install'])


class GuardaDePlataformaTests(unittest.TestCase):

    @unittest.skipUnless(sys.platform != 'win32', 'verifica o aviso fora do Windows')
    def test_main_avisa_que_o_app_e_windows_only(self):
        self.assertEqual(main.main(), 1)


@unittest.skipIf(os.environ.get('SKIP_LIVE') == '1', 'teste de rede desativado (SKIP_LIVE=1)')
class ContratoDaApiDoGithubTests(unittest.TestCase):
    """Confere o contrato real da API que a GUI consome (precisa de rede)."""

    @classmethod
    def setUpClass(cls):
        import requests
        resposta = requests.get(main.GITHUB_RELEASES_API, timeout=30)
        if resposta.status_code != 200:
            raise unittest.SkipTest(f'API respondeu {resposta.status_code}')
        cls.releases = resposta.json()

    def test_todo_asset_usado_e_7z_e_tem_data_parseavel(self):
        assets = [asset for release in self.releases for asset in release['assets']]
        self.assertTrue(assets, 'nenhum asset retornado pela API')
        usados = [asset for asset in assets if asset['name'].endswith('.7z')]
        self.assertTrue(usados, 'nenhum asset .7z na API')
        for asset in usados:
            # fetch_versions() faz strptime exatamente neste formato
            datetime.strptime(asset['updated_at'], "%Y-%m-%dT%H:%M:%SZ")

    def test_release_mais_recente_tem_build_recomendavel_para_64bits(self):
        app = make_app(system_info=SISTEMA_64)
        compativeis = [
            asset['name'] for asset in self.releases[0]['assets']
            if app.is_compatible_version(asset['name'])
        ]
        self.assertTrue(compativeis, f"nenhum build x86_64/seh/ucrt/posix em {self.releases[0]['tag_name']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
