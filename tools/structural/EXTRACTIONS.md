# Extrações do §35 — registro

| extração | commit | diferencial (vs v1.8.2) | custo (5 repos do corpus, mediana de 5) | CI |
|---|---|---|---|---|
| A preparação → `prepare()` | 07b1533 | 0 diferenças em 2.696 chamadas; 8.163 = 2.696 + 5.467 + 0; 0 erros; totais 275·274·0·1 / 304·2·9 / 17·17 | chamadas git iguais (132, 38, 209, 211, 185); tempo −2% a +0,4% | pendente |
| B1 veredito → `decide()` | 54e5b82 | 0 diferenças em 2.696; 8.163 = 2.696 + 5.467 + 0; 0 erros; totais iguais | chamadas git iguais (132, 38, 209, 211, 185); tempo −5% a 0% | pendente |
| B2 varredura → `scan()` | efadbb8 | 0 diferenças em 2.696; 8.163 = 2.696 + 5.467 + 0; 0 erros; totais iguais | chamadas git iguais; tempo −0,8% a +0,6% | pendente |
| B3 stamp/coverage → `assemble()` | 595d2cb | 0 diferenças em 2.696; 8.163 = 2.696 + 5.467 + 0; 0 erros; totais iguais | chamadas git iguais; tempo −0,2% a +0,4% | pendente |
| C apresentação → `report()` | 7a39278 | 0 diferenças em 2.696; 8.163 = 2.696 + 5.467 + 0; 0 erros; totais iguais | chamadas git iguais; tempo −0,6% a +0,4% | run 43620475018 |
| Etapa 4: `make_stamp()` (am. 7) | a4f0f57 | 0 diferenças em 2.696; 8.163 = 2.696 + 5.467 + 0; 0 erros; totais iguais | chamadas git iguais; tempo −1,1% a +0,8% | run 43647221278 |

Custo da A, referência × candidata (s; chamadas git): wrapt 1,744×1,751 (132); python-multipart 0,541×0,543 (38);
starlette 2,689×2,700 (209); uvicorn 2,676×2,661 (211); rich 2,413×2,365 (185). Saídas 2, 0, 1, 0, 1 nos dois.

Custo da B1 (s): wrapt 1,999×1,948; python-multipart 0,614×0,614; starlette 2,959×2,863; uvicorn 3,080×3,031;
rich 2,705×2,578. Saídas iguais. **Uma rodada anterior da B1 foi inválida**: no zsh, `$C:closure_drift.py` é lido
como modificador e a candidata virou arquivo vazio (0,02 s, saída 0). O `cost.py` agora recusa detector vazio e
falha quando as saídas diferem; a rodada inválida não entra em nenhum número.
