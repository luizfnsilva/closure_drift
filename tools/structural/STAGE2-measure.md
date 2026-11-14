# Etapa 2 do §35 — os blocos de `measure()` (detector de 1.8.2, linhas 1423–1741)

Classes: **domínio** (decide o veredito) · **segurança** (recusa entrada perigosa ou ambígua) ·
**compatibilidade** (forma pública do relatório) · **apresentação** (o que se imprime) · **roteamento**.
Nenhum bloco é marcado "possivelmente redundante" nesta etapa: as 6 instruções não executadas são todas texto
de apresentação de ramos reais (ver abaixo), não lógica sem uso.

| linhas | bloco | classe | vai para |
|---|---|---|---|
| 1424–1430 | fonte da versão (`Labels`, `vsrc`); recusa versão derivada da tag com `--at commits` | domínio, segurança | A preparação |
| 1431–1439 | `--version-regex` inválida ou sem grupo → recusa antes de ler | segurança | A |
| 1440–1441 | closure (`include`, `Closure`) | domínio | A |
| 1443–1446 | `--compare` → `compare()`, `--tag` → `check_tag()` | roteamento | fica |
| 1448–1471 | pontos de publicação; nenhum ponto → nota e saída 2 (**imprime JSON ou stderr aqui**) | domínio + apresentação | B, com a impressão mantida no mesmo ponto |
| 1473–1474 | sem fonte de versão em lugar nenhum → recusa | segurança | B |
| 1476–1501 | laço de medição: closure por ponto, label, churn, vazios | domínio | B |
| 1503–1527 | fontes contraditas (votação das tags em `--at commits`), rejeitados | domínio, segurança | B |
| 1529–1530 | nada rotulado → recusa | segurança | B |
| 1531–1542 | **cabeçalho em texto, impresso no meio da medição** | apresentação | ver "ordem" |
| 1544–1562 | igualdade por versão, `drifting`, `worst`, mecanismos, famílias de tag | domínio | B |
| 1564–1601 | `stamp` e `coverage` | compatibilidade (campos do JSON) | B (monta), C (emite) |
| 1603–1605 | `--would-tag` → `would_tag()` | roteamento | fica |
| 1607–1621 | **veredito e código de saída** | domínio (núcleo) | B, função própria |
| 1623–1630 | `--explain` (pode recusar) | domínio, segurança | B |
| 1632–1655 | `--badge`, `--json` | apresentação, compatibilidade | C |
| 1657–1741 | relatório em texto | apresentação | C |

## A ordem que o diferencial tem de preservar
O cabeçalho em texto (1531–1542) sai **antes** de `--explain` poder recusar (1623–1630). Hoje, uma recusa do
`--explain` deixa o cabeçalho no stdout e a recusa no stderr. Mover o cabeçalho para a camada C mudaria o
stdout nesse caminho. A extração C mantém essa ordem (o cabeçalho é impresso entre B-medição e B-veredito,
ou o explain é resolvido antes do cabeçalho só se o diferencial provar igualdade — não se presume).
O mesmo vale para 1448–1471: a nota de "nenhum ponto" é emitida antes de qualquer outra saída.

## As 6 instruções não executadas de `measure()`
- 1667 — "... and N more labels": relatório em texto com mais de 25 labels. Apresentação de caso real; falta prova.
- 1717–1719 — texto do `incomplete` por fonte contradita. O ramo de veredito é exercitado (JSON); o texto não.
- 1729–1730 — texto do `incomplete` genérico (conflito de fontes ou `--strict`). Idem.
Classe: apresentação, com justificativa documentada (§16.5, §20). Não são candidatas a remoção; são provas que
faltam. Ficam listadas para a 1.9.0 acrescentar três provas de texto, sem mudar código.

## Extrações, na ordem
A: 1424–1441 → `prepare(a, objects, head_sha, at, vfile, vregex, cfg)` devolvendo uma tupla.
B: 1448–1530 e 1544–1601 → `scan(...)` e `assemble(...)`; 1607–1621 → `decide(...)`.
C: 1632–1741 → `report(...)`, com o cabeçalho mantido no ponto atual.
Cada uma num commit, diferencial inteiro verde antes da seguinte.
