#!/usr/bin/env python3
"""Fail when the version label does not name one state across the files that declare it.

The 0.7.0 tag was pushed with `VERSION` at 0.7.0 and `CITATION.cff` at 0.6.0, and every check in
this repository was green. That is the defect this tool measures, in the repository of the tool that
measures it. This is the step that would have stopped it.

    python3 tools/conferir_versao.py              # the files must agree
    python3 tools/conferir_versao.py --tag v0.7.1 # and the tag must agree with them

Exit 0 if they agree, 1 if they do not, 2 if a source could not be read.
Zero dependencies.
"""
import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def ler(nome, padrao=None, primeiro_cabecalho=False):
    caminho = RAIZ / nome
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError as e:
        print("cannot read %s: %s" % (nome, e), file=sys.stderr)
        raise SystemExit(2)
    if primeiro_cabecalho:
        m = re.search(r"(?m)^##\s+(\d+\.\d+\.\d+)\b", texto)
    else:
        m = re.search(padrao, texto)
    if not m:
        print("no version found in %s" % nome, file=sys.stderr)
        raise SystemExit(2)
    return m.group(1).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="tag name being pushed, e.g. v0.7.1")
    a = ap.parse_args()

    fontes = {
        "VERSION": ler("VERSION", r"(\d+\.\d+\.\d+)"),
        "CITATION.cff": ler("CITATION.cff", r"(?m)^version:\s*(\S+)\s*$"),
        "CHANGELOG.md (first entry)": ler("CHANGELOG.md", primeiro_cabecalho=True),
        "closure_drift.py __version__": ler("closure_drift.py", r'(?m)^__version__\s*=\s*"([^"]+)"'),
    }
    # The MCP entry and the container it names (§34 R18-10): one version, read, not remembered.
    fontes["server.json version"] = ler("integrations/mcp/server.json", r'(?m)^  "version":\s*"([^"]+)"')
    fontes["server.json image"] = ler("integrations/mcp/server.json", r'closure_drift:(\d+\.\d+\.\d+)"')
    fontes["closure_drift_mcp.py serverInfo"] = ler(
        "closure_drift_mcp.py", r'"serverInfo":\s*\{"name":\s*"closure_drift",\s*"version":\s*"([^"]+)"')
    if a.tag:
        fontes["tag"] = a.tag[1:] if a.tag.startswith("v") else a.tag

    for nome, valor in fontes.items():
        print("  %-28s %s" % (nome, valor))

    # Pins in the docs a reader copies (1.7.0): every one names this release, or the run fails.
    pin = re.compile(r"closure_drift@v(\d+\.\d+\.\d+)|closure-drift@v(\d+\.\d+\.\d+)"
                     r"|releases/download/v(\d+\.\d+\.\d+)/|closure_drift-(\d+\.\d+\.\d+)-py3"
                     r"|^\s*rev: v(\d+\.\d+\.\d+)|closure_drift/v(\d+\.\d+\.\d+)/closure_drift\.py"
                     r"|ghcr\.io/luizfnsilva/closure_drift:(\d+\.\d+\.\d+)", re.M)
    for doc in ("README.md", "docs/USAGE.md", "docs/CI.md", "integrations/README.md"):
        texto = (RAIZ / doc).read_text(encoding="utf-8")
        for m in pin.finditer(texto):
            linha = texto.count("\n", 0, m.start()) + 1
            fontes["%s:%d" % (doc, linha)] = next(g for g in m.groups() if g)

    distintos = set(fontes.values())
    if len(distintos) > 1:
        print("\nVERSION MISMATCH: the label names %d different states: %s"
              % (len(distintos), ", ".join(sorted(distintos))), file=sys.stderr)
        return 1
    print("\nversion agrees across %d sources: %s" % (len(fontes), distintos.pop()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
