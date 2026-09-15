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
    }
    if a.tag:
        fontes["tag"] = a.tag[1:] if a.tag.startswith("v") else a.tag

    for nome, valor in fontes.items():
        print("  %-28s %s" % (nome, valor))

    distintos = set(fontes.values())
    if len(distintos) > 1:
        print("\nVERSION MISMATCH: the label names %d different states: %s"
              % (len(distintos), ", ".join(sorted(distintos))), file=sys.stderr)
        return 1
    print("\nversion agrees across %d sources: %s" % (len(fontes), distintos.pop()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
