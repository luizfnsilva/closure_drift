#!/usr/bin/env python3
"""Depositar uma versão nova no Zenodo, sob o mesmo conceito, e devolver o DOI da versão.

O token NUNCA é argumento de linha de comando (ficaria no histórico do shell e na lista de
processos): lê-se de ZENODO_TOKEN no ambiente. Este programa não o imprime, nem o grava.

    export ZENODO_TOKEN=...            # numa sessão que você fecha depois
    python3 tools/depositar_zenodo.py            # ensaio: diz o que faria e para
    python3 tools/depositar_zenodo.py --publicar # deposita e PUBLICA (irreversível)

Deposita exatamente os nove arquivos que DEPOSIT.sha256 governa, confere os resumos contra o
manifesto antes de subir, e recusa se algum divergir. Só biblioteca padrão.
"""
import argparse, hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://zenodo.org/api"
CONCEITO = "21763931"          # concept DOI 10.5281/zenodo.21763931
ULTIMO_REGISTRO = "22341979"   # a versão 0.6.0, de onde se deriva a nova


def manifesto():
    nove = {}
    for l in open(os.path.join(RAIZ, "DEPOSIT.sha256"), encoding="utf-8"):
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        h, nome = l.split(None, 1)
        nove[nome.strip()] = h
    return nove


def conferir(nove):
    ruins = []
    for nome, esperado in nove.items():
        caminho = os.path.join(RAIZ, nome)
        if not os.path.isfile(caminho):
            ruins.append((nome, "ausente")); continue
        obtido = hashlib.sha256(open(caminho, "rb").read()).hexdigest()
        if obtido != esperado:
            ruins.append((nome, "resumo diverge"))
    return ruins


def pedir(metodo, url, token, dados=None, binario=None, tipo="application/json"):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + urllib.parse.urlencode({"access_token": token}), method=metodo)
    corpo = None
    if binario is not None:
        corpo = binario; req.add_header("Content-Type", "application/octet-stream")
    elif dados is not None:
        corpo = json.dumps(dados).encode("utf-8"); req.add_header("Content-Type", tipo)
    try:
        with urllib.request.urlopen(req, corpo, timeout=120) as r:
            bruto = r.read()
            return json.loads(bruto) if bruto else {}
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="replace")[:400]
        raise SystemExit("Zenodo %s %s: %s\n%s" % (metodo, url.split("?")[0], e.code, detalhe))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true", help="publica de facto (irreversível: minta o DOI)")
    a = ap.parse_args()

    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        raise SystemExit("ZENODO_TOKEN não está no ambiente. Exporte-o nesta sessão e torne a rodar.\n"
                         "Este programa não aceita o token por argumento, de propósito.")

    versao = open(os.path.join(RAIZ, "VERSION"), encoding="utf-8").read().strip()
    nove = manifesto()
    ruins = conferir(nove)
    if ruins:
        for nome, razao in ruins:
            print("  %-34s %s" % (nome, razao), file=sys.stderr)
        raise SystemExit("os nove arquivos não batem com DEPOSIT.sha256 — nada foi enviado.")
    print("versão %s · %d arquivos conferidos contra o manifesto" % (versao, len(nove)))

    if not a.publicar:
        print("\nENSAIO. Nada foi enviado. O que a corrida com --publicar faria:")
        print("  1. abrir uma versão nova do registro %s (conceito %s)" % (ULTIMO_REGISTRO, CONCEITO))
        print("  2. limpar os arquivos herdados e subir estes nove:")
        for nome in sorted(nove): print("       %s" % nome)
        print("  3. pôr a versão %s nos metadados" % versao)
        print("  4. PUBLICAR — irreversível — e imprimir o DOI da versão")
        return 0

    print("abrindo versão nova…")
    novo = pedir("POST", "%s/deposit/depositions/%s/actions/newversion" % (API, ULTIMO_REGISTRO), token)
    rascunho = novo["links"]["latest_draft"]
    dep = pedir("GET", rascunho, token)
    dep_id = dep["id"]

    for f in pedir("GET", "%s/deposit/depositions/%s/files" % (API, dep_id), token):
        pedir("DELETE", "%s/deposit/depositions/%s/files/%s" % (API, dep_id, f["id"]), token)
    print("rascunho %s · arquivos herdados removidos" % dep_id)

    balde = dep["links"]["bucket"]
    for nome in sorted(nove):
        with open(os.path.join(RAIZ, nome), "rb") as fh:
            pedir("PUT", "%s/%s" % (balde, urllib.parse.quote(nome)), token, binario=fh.read())
        print("  subiu  %s" % nome)

    meta = dict(dep.get("metadata", {})); meta["version"] = versao
    meta.pop("doi", None); meta.pop("prereserve_doi", None)
    pedir("PUT", "%s/deposit/depositions/%s" % (API, dep_id), token, dados={"metadata": meta})

    pub = pedir("POST", "%s/deposit/depositions/%s/actions/publish" % (API, dep_id), token)
    doi = pub.get("doi") or pub.get("metadata", {}).get("doi")
    print("\nPUBLICADO\n  DOI da versão: %s\n  registro: %s" % (doi, pub.get("record_id")))
    print("\nFalta um passo, e é aqui: escreva esse DOI na linha do cabeçalho de DEPOSIT.sha256,\n"
          "comite e empurre. Os resumos não mudam; a linha é comentário.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
