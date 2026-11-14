# Extrações do §35 — registro

| extração | commit | diferencial (vs v1.8.2) | custo (5 repos do corpus, mediana de 5) | CI |
|---|---|---|---|---|
| A preparação → `prepare()` | 07b1533 | 0 diferenças em 2.696 chamadas; 8.163 = 2.696 + 5.467 + 0; 0 erros; totais 275·274·0·1 / 304·2·9 / 17·17 | chamadas git iguais (132, 38, 209, 211, 185); tempo −2% a +0,4% | pendente |

Custo da A, referência × candidata (s; chamadas git): wrapt 1,744×1,751 (132); python-multipart 0,541×0,543 (38);
starlette 2,689×2,700 (209); uvicorn 2,676×2,661 (211); rich 2,413×2,365 (185). Saídas 2, 0, 1, 0, 1 nos dois.
