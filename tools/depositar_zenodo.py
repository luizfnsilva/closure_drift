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
import argparse
import re
import textwrap, hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://zenodo.org/api"
CONCEITO = "21763931"          # concept DOI 10.5281/zenodo.21763931
ULTIMO_REGISTRO = "22770460"   # a versão 0.6.0, de onde se deriva a nova


ARQUIVO_DO_TOKEN = os.path.expanduser("~/.config/zenodo.token")
DESCRICAO = "tools/zenodo-description.html"


def ler_token():
    """O token vem do ambiente ou de um arquivo só-do-dono. Nunca de argumento de linha de
    comando — ali ficaria no histórico do shell e na lista de processos — e nunca impresso."""
    def conferido(t, origem):
        t = (t or "").strip()
        if t and len(t) < 40:
            raise SystemExit(
                "RECUSADO — o token vindo de %s tem %d caracteres, e um do Zenodo tem cerca de 60.\n"
                "Um fragmento passa despercebido: o Zenodo trata o pedido como NAO autenticado e\n"
                "responde com erro de validacao ou 403, que mandam procurar defeito no lugar errado."
                % (origem, len(t)))
        return t

    do_ambiente = os.environ.get("ZENODO_TOKEN")
    if do_ambiente:
        return conferido(do_ambiente, "ZENODO_TOKEN")
    if os.path.isfile(ARQUIVO_DO_TOKEN):
        modo = os.stat(ARQUIVO_DO_TOKEN).st_mode & 0o777
        if modo & 0o077:
            raise SystemExit("%s está legível por outros (modo %o). Corrija e torne a rodar:\n"
                             "    chmod 600 %s" % (ARQUIVO_DO_TOKEN, modo, ARQUIVO_DO_TOKEN))
        with open(ARQUIVO_DO_TOKEN, encoding="utf-8") as fh:
            t = conferido(fh.read(), ARQUIVO_DO_TOKEN)
        if t:
            return t
        raise SystemExit("%s está vazio." % ARQUIVO_DO_TOKEN)
    raise SystemExit(
        "Não achei o token. Dois lugares, nesta ordem:\n"
        "  1. a variável ZENODO_TOKEN, exportada na sessão que roda este programa; ou\n"
        "  2. o arquivo %s, só do dono:\n"
        "         umask 077 && printf %%s '<token>' > %s\n"
        "         chmod 600 %s\n"
        "Por desenho, este programa não aceita o token por argumento." % (
            ARQUIVO_DO_TOKEN, ARQUIVO_DO_TOKEN, ARQUIVO_DO_TOKEN))


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


def resumo_html(descricao, paragrafos=2, largura=94):
    """Os ultimos paragrafos da descricao, em texto, para o ensaio nao mentir sobre o que envia.

    O ensaio existe para que o defeito seja visivel ANTES de ser irreversivel. Um ensaio que nao
    mostra os metadados deixa o operador conferir os arquivos e nao o primeiro texto que qualquer
    visitante do registro le.
    """
    partes = re.findall(r"<p>(.*?)</p>", descricao, flags=re.S) or [descricao]
    linhas = []
    for bruto in partes[-paragrafos:]:
        texto = re.sub(r"<[^>]+>", "", bruto)
        for entidade, char in (("&mdash;", "—"), ("&quot;", '"'), ("&amp;", "&"),
                               ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
            texto = texto.replace(entidade, char)
        linhas.extend(textwrap.wrap(" ".join(texto.split()), largura) or [""])
        linhas.append("")
    if len(partes) > paragrafos:
        linhas.insert(0, "(... %d paragrafo(s) anterior(es) nao mostrado(s); os ultimos %d seguem)"
                      % (len(partes) - paragrafos, paragrafos))
        linhas.insert(1, "")
    return [l for l in linhas]


def metadados(versao):
    """A descricao e a data do registro, lidas do repositorio — nunca herdadas do rascunho.

    Herdar era o comportamento antigo, e o registro novo nasceria com o texto da versao anterior:
    medido no registro 0.6.0, uma descricao de 4.836 caracteres nomeando da5da3c0... como a
    identidade do script, sem nenhuma ocorrencia de 6d8906ef nem de 0.7, e publication_date de
    2026-09-05. O primeiro texto que qualquer visitante le descreveria um arquivo que nao esta
    anexado ao registro.
    """
    caminho = os.path.join(RAIZ, DESCRICAO)
    try:
        with open(caminho, encoding="utf-8") as fh:
            descricao = fh.read().strip()
    except OSError as e:
        raise SystemExit("nao li %s: %s — o registro nao nasce com descricao herdada." % (DESCRICAO, e))

    if versao not in descricao:
        raise SystemExit(
            "%s nao menciona a versao %s.\n"
            "A descricao do registro e cumulativa: um paragrafo por versao. Acrescente o desta\n"
            "antes de depositar — o registro nao nasce descrevendo a versao anterior." % (DESCRICAO, versao))

    data = None
    with open(os.path.join(RAIZ, "CHANGELOG.md"), encoding="utf-8") as fh:
        for linha in fh:
            m = re.match(r"^##\s+" + re.escape(versao) + r"\s+[—-]\s+(\d{4}-\d{2}-\d{2})", linha)
            if m:
                data = m.group(1)
                break
    if not data:
        raise SystemExit(
            "CHANGELOG.md nao tem entrada datada para %s.\n"
            "A data de publicacao do registro sai dali, e nao do relogio nem do rascunho." % versao)
    return descricao, data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true", help="publica de facto (irreversível: minta o DOI)")
    a = ap.parse_args()

    token = ler_token()

    versao = open(os.path.join(RAIZ, "VERSION"), encoding="utf-8").read().strip()
    descricao, data = metadados(versao)
    nove = manifesto()

    # Duas entradas com o mesmo basename colidiriam numa chave so, e o deposito ficaria com um
    # arquivo a menos sem que nada reclamasse. Recusa nomeada, antes de qualquer chamada de rede.
    planos = {}
    for nome in nove:
        planos.setdefault(os.path.basename(nome), []).append(nome)
    colididos = {k: v for k, v in planos.items() if len(v) > 1}
    if colididos:
        for k, v in sorted(colididos.items()):
            print("  %s  <-  %s" % (k, ", ".join(sorted(v))), file=sys.stderr)
        raise SystemExit("dois arquivos do manifesto teriam o mesmo nome no deposito — nada foi enviado.")

    ruins = conferir(nove)
    if ruins:
        for nome, razao in ruins:
            print("  %-34s %s" % (nome, razao), file=sys.stderr)
        raise SystemExit("os nove arquivos não batem com DEPOSIT.sha256 — nada foi enviado.")
    print("versão %s · %d arquivos conferidos contra o manifesto" % (versao, len(nove)))

    if not a.publicar:
        print("\nENSAIO. Nada foi enviado. O que a corrida com --publicar faria:")
        print("  1. abrir uma versão nova do registro %s (conceito %s)" % (ULTIMO_REGISTRO, CONCEITO))
        print("  2. limpar os arquivos herdados e subir estes nove, com o nome PLANO que o")
        print("     registro usa desde 0.4.0 (a 0.3.0 depositou quatro arquivos e nenhuma bateria):")
        for nome in sorted(nove):
            chave = os.path.basename(nome)
            print("       %s%s" % (chave, "" if chave == nome else "   (de %s)" % nome))
        print("  3. escrever ESTES metadados (nada e herdado do rascunho):")
        print("       version          %s" % versao)
        print("       publication_date %s   (do cabecalho do CHANGELOG)" % data)
        print("       description      %s, de %s:" % (len(descricao), DESCRICAO))
        print()
        for linha in resumo_html(descricao):
            print("     | %s" % linha)
        print()
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
        # O registro guarda nomes PLANOS: o arquivo que no repositorio vive em tests/ foi depositado
        # como fixture_label_only.py de 0.4.0 a 0.6.0, e tools/verify_deposit.py casa a chave do
        # registro contra um indice por basename. Subir com o caminho mudaria o nome do arquivo no
        # deposito e quebraria o conferidor contra o registro novo.
        chave = os.path.basename(nome)
        with open(os.path.join(RAIZ, nome), "rb") as fh:
            pedir("PUT", "%s/%s" % (balde, urllib.parse.quote(chave)), token, binario=fh.read())
        print("  subiu  %s%s" % (chave, "" if chave == nome else "   (de %s)" % nome))

    meta = dict(dep.get("metadata", {}))
    meta["version"] = versao
    meta["description"] = descricao
    meta["publication_date"] = data
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
