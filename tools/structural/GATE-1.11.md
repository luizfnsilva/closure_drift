# Portão da 1.11 (§37)

Diferencial contra a v1.10.0 (c7b0225), candidata d06b8a9: 8.181 chamadas vistas = 2.702 comparadas + 5.479
excluídas + 0 não concluídas; erros do harness 0; `calls.jsonl` 7e70ff80…. Duas diferenças, ambas o texto de uso
com `--evidence`. Bateria, adversarial e propriedades verdes sob o hook (PR05 inclusive).

Primeira rodada (com `closure_commits` sempre presente): 1.360 diferenças e PR05 vermelha em 26 de 60 sementes —
motivo da emenda 2.

Verificador: 8 de 8 edições com o código esperado (`tests/verify_adversarial.py`); 8 de 8 mutantes pegos
(`tests/verify_mutants.py`). V02 escapou na primeira rodada (emenda 1).
