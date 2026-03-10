"""
Monitor de resultados do iRacing via watchdog.

Observa a pasta configurada (tipicamente `aiseasons`) e dispara callback
quando um JSON estiver pronto para leitura.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileMovedEvent
    from watchdog.observers import Observer

    _WATCHDOG_DISPONIVEL = True
except ImportError:  # pragma: no cover - depende de pacote externo opcional.
    FileSystemEventHandler = object  # type: ignore[assignment]
    FileSystemEvent = object  # type: ignore[assignment]
    FileMovedEvent = object  # type: ignore[assignment]
    Observer = None  # type: ignore[assignment]
    _WATCHDOG_DISPONIVEL = False


CallbackResultado = Callable[[str], bool | None]


class MonitorResultados(FileSystemEventHandler):
    """Handler que detecta novos arquivos JSON de resultado."""

    def __init__(self, callback: CallbackResultado):
        super().__init__()
        self.callback = callback
        self._processando: set[str] = set()
        self._assinatura_processada: dict[str, tuple[int, int]] = {}
        self._ultima_tentativa: dict[str, float] = {}
        self._lock = threading.Lock()

    def on_created(self, event: FileSystemEvent) -> None:
        self._tratar_evento(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._tratar_evento(event)

    def on_moved(self, event: FileMovedEvent) -> None:
        if getattr(event, "is_directory", False):
            return
        caminho_destino = str(getattr(event, "dest_path", "") or "").strip()
        if caminho_destino:
            self._enfileirar_processamento(caminho_destino)

    def _tratar_evento(self, event: FileSystemEvent) -> None:
        if getattr(event, "is_directory", False):
            return

        caminho = str(getattr(event, "src_path", "") or "").strip()
        if not caminho:
            return

        self._enfileirar_processamento(caminho)

    def _enfileirar_processamento(self, caminho_arquivo: str) -> None:
        caminho = os.path.normpath(caminho_arquivo)
        if not caminho.lower().endswith(".json"):
            return

        agora = time.monotonic()
        with self._lock:
            if caminho in self._processando:
                return

            ultima = self._ultima_tentativa.get(caminho, 0.0)
            if agora - ultima < 0.75:
                return

            self._ultima_tentativa[caminho] = agora
            self._processando.add(caminho)

        worker = threading.Thread(
            target=self._aguardar_e_processar,
            args=(caminho,),
            daemon=True,
        )
        worker.start()

    def _aguardar_e_processar(self, caminho: str) -> None:
        try:
            if not self._aguardar_arquivo_estavel(caminho):
                return

            assinatura = self._obter_assinatura_arquivo(caminho)
            if assinatura is None:
                return

            with self._lock:
                if self._assinatura_processada.get(caminho) == assinatura:
                    return

            try:
                sucesso = self.callback(caminho)
            except Exception as erro:
                print(f"Erro no callback do monitor ({caminho}): {erro}")
                return

            if sucesso is not True:
                return

            with self._lock:
                self._assinatura_processada[caminho] = assinatura
        finally:
            with self._lock:
                self._processando.discard(caminho)

    @staticmethod
    def _aguardar_arquivo_estavel(
        caminho: str,
        timeout_segundos: float = 12.0,
        intervalo_segundos: float = 0.35,
        ciclos_estaveis: int = 3,
    ) -> bool:
        inicio = time.monotonic()
        tamanho_anterior = -1
        estaveis = 0

        while time.monotonic() - inicio < timeout_segundos:
            if not os.path.isfile(caminho):
                estaveis = 0
                time.sleep(intervalo_segundos)
                continue

            try:
                tamanho = os.path.getsize(caminho)
            except OSError:
                estaveis = 0
                time.sleep(intervalo_segundos)
                continue

            if tamanho <= 0:
                estaveis = 0
                time.sleep(intervalo_segundos)
                continue

            if tamanho == tamanho_anterior:
                estaveis += 1
                if estaveis >= ciclos_estaveis:
                    return True
            else:
                tamanho_anterior = tamanho
                estaveis = 0

            time.sleep(intervalo_segundos)

        return False

    @staticmethod
    def _obter_assinatura_arquivo(caminho: str) -> tuple[int, int] | None:
        try:
            stat = os.stat(caminho)
        except OSError:
            return None
        return int(stat.st_size), int(stat.st_mtime_ns)


class MonitorIRacing:
    """Gerencia o ciclo de vida do Observer de resultados."""

    def __init__(
        self,
        pasta_monitorada: str,
        callback: CallbackResultado,
        recursive: bool = True,
    ):
        self.pasta_monitorada = os.path.normpath(str(pasta_monitorada or "").strip())
        self.callback = callback
        self.recursive = bool(recursive)
        self.observer: Observer | None = None
        self.rodando = False

    @staticmethod
    def watchdog_disponivel() -> bool:
        return _WATCHDOG_DISPONIVEL and Observer is not None

    def iniciar(self) -> bool:
        """Inicia o monitoramento da pasta configurada."""
        if self.rodando:
            return True

        if not self.watchdog_disponivel():
            print("Watchdog nao instalado. Execute: pip install watchdog")
            return False

        if not self.pasta_monitorada:
            print("Pasta monitorada nao configurada.")
            return False

        try:
            os.makedirs(self.pasta_monitorada, exist_ok=True)
        except OSError as erro:
            print(f"Erro ao preparar pasta monitorada: {erro}")
            return False

        try:
            self.observer = Observer()
            handler = MonitorResultados(self.callback)
            self.observer.schedule(
                handler,
                self.pasta_monitorada,
                recursive=self.recursive,
            )
            self.observer.start()
            self.rodando = True
            print(f"Monitor de resultados ativo em: {self.pasta_monitorada}")
            return True
        except Exception as erro:
            self.observer = None
            self.rodando = False
            print(f"Erro ao iniciar monitor de resultados: {erro}")
            return False

    def parar(self) -> None:
        """Para o monitoramento."""
        if not self.observer:
            self.rodando = False
            return

        try:
            self.observer.stop()
            self.observer.join(timeout=2)
        except Exception:
            pass
        finally:
            self.observer = None
            self.rodando = False
            print("Monitor de resultados parado.")

    def esta_rodando(self) -> bool:
        return self.rodando
