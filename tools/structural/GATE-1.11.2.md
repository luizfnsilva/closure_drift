# Portão da 1.11.2 (§38.3 arquivo de grafts)

Diferencial contra a v1.11.1 (7c78f61), candidata 6287271 (sha256 `9fb21f6e…`): 8.208 chamadas vistas = 2.711
comparadas; erros do harness 0; nenhuma chamada sem conclusão; `calls.jsonl` 44948ea7…. Uma diferença, a que o
§38.3 permite: GF01 (`clean`/0 → `drift`/1 com `.git/info/grafts` cortando o histórico em `--at commits`).
A emenda 1 tirou a outra que apareceu na primeira rodada (aviso do git no stderr da SR03).

Bateria 286 declaradas · 285 verdes · 0 vermelhas · 1 não rodou. Adversarial 315 ataques · 304 como exigido ·
2 frouxos conhecidos (ZA02, ZA04). Propriedades 17/17. Mutantes 88/88 pegos pela prova exigida, M88 → GF01;
controle positivo íntegro. CI 44128276783: baterias e controles negativos verdes em Linux, macOS e Windows; as duas
conferências dos nove arquivos ficam para o commit de versão.
