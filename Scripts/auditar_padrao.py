"""Auditoria leve de padrao para o projeto Modo Carreira.

Uso rapido:
  python Scripts/auditar_padrao.py --root . --paths Logica/mercado/mercado_manager.py
  python Scripts/auditar_padrao.py --root .
"""

from __future__ import annotations

import argparse
import ast
import codecs
import re
from pathlib import Path

TARGET_DIRS = ("Dados", "Logica", "UI", "Utils")
IGNORE_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
}
SNAKE_FILE_RE = re.compile(r"^[a-z][a-z0-9_]*\.py$")
MAX_FILE_LINES_WARN = 1200
MAX_FUNC_LINES_WARN = 180
MAX_LINE_LEN_WARN = 120


class AuditResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.files_checked = 0

    def add_error(self, path: Path, message: str) -> None:
        self.errors.append(f"[ERROR] {path.as_posix()}: {message}")

    def add_warning(self, path: Path, message: str) -> None:
        self.warnings.append(f"[WARN]  {path.as_posix()}: {message}")


def _iter_python_files(root: Path, paths: list[str] | None) -> list[Path]:
    if paths:
        out: list[Path] = []
        for raw in paths:
            p = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
            if p.is_file() and p.suffix == ".py":
                out.append(p)
        return sorted(set(out))

    out = []
    for directory in TARGET_DIRS:
        base = root / directory
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(part in IGNORE_DIR_NAMES for part in path.parts):
                continue
            out.append(path.resolve())
    return sorted(set(out))


def _is_logica_or_ui(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return rel.parts and rel.parts[0] in {"Logica", "UI"}


def _is_dados_or_logica(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return rel.parts and rel.parts[0] in {"Dados", "Logica"}


def _check_file(path: Path, root: Path, result: AuditResult) -> None:
    result.files_checked += 1

    try:
        raw = path.read_bytes()
        had_bom = raw.startswith(codecs.BOM_UTF8)
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        result.add_error(path, f"arquivo nao esta em UTF-8: {exc}")
        return
    except OSError as exc:
        result.add_error(path, f"nao foi possivel ler arquivo: {exc}")
        return

    if had_bom:
        result.add_warning(path, "arquivo usa UTF-8 com BOM")

    lines = text.splitlines()
    line_count = len(lines)

    if line_count > MAX_FILE_LINES_WARN:
        result.add_warning(path, f"arquivo com {line_count} linhas (limite recomendado: {MAX_FILE_LINES_WARN})")

    long_lines = [idx + 1 for idx, line in enumerate(lines) if len(line) > MAX_LINE_LEN_WARN]
    if long_lines:
        preview = ", ".join(str(n) for n in long_lines[:8])
        extra = "" if len(long_lines) <= 8 else ", ..."
        result.add_warning(path, f"{len(long_lines)} linha(s) acima de {MAX_LINE_LEN_WARN} caracteres: {preview}{extra}")

    filename = path.name
    if filename != "__init__.py" and not SNAKE_FILE_RE.fullmatch(filename):
        result.add_warning(path, "nome de arquivo fora de snake_case")

    if "LEGACY_BACKUP" in text:
        result.add_warning(path, "marca LEGACY_BACKUP encontrada")

    if _is_dados_or_logica(path, root) and "print(" in text:
        result.add_warning(path, "uso de print() em camada de dados/logica; preferir logging")

    if _is_logica_or_ui(path, root) and "from __future__ import annotations" not in "\n".join(lines[:10]):
        result.add_warning(path, "modulo sem 'from __future__ import annotations' no topo")

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        result.add_error(path, f"erro de sintaxe: linha {exc.lineno}: {exc.msg}")
        return

    if not ast.get_docstring(tree):
        result.add_warning(path, "docstring de modulo ausente")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)
            if start is None or end is None:
                continue
            size = end - start + 1
            if size > MAX_FUNC_LINES_WARN:
                result.add_warning(path, f"funcao '{node.name}' com {size} linhas (limite recomendado: {MAX_FUNC_LINES_WARN})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditar padrao tecnico de arquivos Python.")
    parser.add_argument("--root", default=".", help="Diretorio raiz do projeto.")
    parser.add_argument("--paths", nargs="*", help="Lista de caminhos relativos/absolutos para auditar.")
    parser.add_argument("--strict", action="store_true", help="Retornar erro quando houver warnings.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    files = _iter_python_files(root, args.paths)

    if not files:
        print("Nenhum arquivo Python encontrado para auditoria.")
        return 0

    result = AuditResult()
    for path in files:
        _check_file(path, root, result)

    print(f"Arquivos auditados: {result.files_checked}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Errors: {len(result.errors)}")

    for message in result.errors:
        print(message)
    for message in result.warnings:
        print(message)

    if result.errors:
        return 1
    if args.strict and result.warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
