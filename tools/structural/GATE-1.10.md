# Portão da 1.10 (§36) — 15/11/2026

Diferencial contra v1.9.0, candidata a159a43 (= release-1.10.0 salvo `__version__` e docs).
8.181 vistas = 2.702 comparadas + 5.479 excluídas + 0 não concluídas; 0 erros do harness.
Diferenças: 1.126, todas permitidas pelo `allowed36.py`: 1.125 só a linha `reason:`/chave `reason_code`,
1 recusa `--tag` sem label com a primeira linha que nomeia o workflow (am. 2). Códigos de saída: iguais em todas.
Nenhum `reason_code` no nível de cima de um veredito decidido.

O classificador foi corrigido três vezes depois de ver o log (quebra de linha final; `reason_code` aninhado de
componentes; a regra "decidido sem código" restrita ao nível de cima, porque um componente sem decisão leva o
seu). Controle positivo depois das correções: sobre o log do controle positivo da 1.9.0 (código de saída e
textos plantados) ele reprova as 198 diferenças (176 de saída, 22 de texto), saída 1.

Baterias com o gancho: 280 · 279 · 0 · 1; propriedades 17 · 17. Adversarial 303 · 3 loose: o terceiro era ZX05
(`reason_code` não documentado em docs/REPORT.md), conserto de documentação; depois, sem gancho, 304 · 2 · 9.
Custo (5 repos): chamadas git iguais; tempo −1,6% a +0,5%.
