# Portão da 1.11.1 (§38.1 D1, §38.2 clone raso)

Diferencial contra a v1.11.0 (428cd00), candidata 404285e (sha256 `b24bae94…`): 8.196 chamadas vistas = 2.707
comparadas; erros do harness 0; nenhuma chamada sem conclusão; `calls.jsonl` 500cdd70…. Duas diferenças, as que o
§38.2 permite: SH01 (`clean`/0 → `incomplete`/2, `shallow_history`) e SH02 (`drift`/1 nos dois, mais o campo
`history_shallow`). Bateria 284 declaradas · 283 verdes · 0 vermelhas · 1 não rodou; adversarial e propriedades
verdes sob o hook.

D1 (Action em relatório de componentes): ACT08 vermelha na `action.yml` da 1.11.0, verde depois; mutante M86.
