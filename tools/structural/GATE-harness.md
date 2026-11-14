# Portão do harness diferencial (§35 am. 3–6) — 14/11/2026

Terceira rodada; as duas primeiras reprovaram e geraram as emendas 5 e 6.

## Controle nulo (candidata = referência)
```
reference v1.8.2 a547896441c9ca716f36eb6e822d9d8653ecc4b6 c50974fcb4a5eb6cb51302dbc767a11a427343d9c88e397caab5d3156743edb4
candidate 8ec5f84788e53e30a40cd722ff7231f21819fd67 c50974fcb4a5eb6cb51302dbc767a11a427343d9c88e397caab5d3156743edb4
hook 9d8ab2b296bb600efb12f1d98386350aef372d790447e45b7f5c15e15fb9462c
seen 8163  start 2696  end 2696  call 2696  harness_error 0  
differ 0  compared_of_seen 2696/8163
calls.jsonl ef8c6e8e3fb70a9707f83a3d4204d7db8b7331350f0eca95d3a48ceb780e52cc
seen 8163 = compared 2696 + excluded 5467 (inner 5462: 2x2696 + 70 self-calls; module_call 4; other 1) + not concluded 0
start 2696 end 2696 call 2696 harness_error 0 differ 0
ok    seen = compared + excluded
ok    compared = start
ok    start = end + not concluded
ok    call = end
ok    inner = 2 x compared + self-calls (self-calls >= 0)
ok    no harness_error
ok    no call left unconcluded
ok    zero differences (null control or candidate)
275 declared · 274 green · 0 red · 1 not run
315 attacks · 304 as required · 2 loose · 9 not run
17 properties · 17 green · 0 red · 0 known and open · 0 not run
```
Totais com o gancho = sem o gancho (bateria 275·274·0·1, adversarial 304·2·9, propriedades 17·17).

## Controle positivo (três mudanças plantadas: código de saída, texto de stdout, texto de recusa)
```
reference v1.8.2 a547896441c9ca716f36eb6e822d9d8653ecc4b6 c50974fcb4a5eb6cb51302dbc767a11a427343d9c88e397caab5d3156743edb4
candidate 8ec5f84788e53e30a40cd722ff7231f21819fd67 7f6e34f97657c5843a10e479fd144ad1bfa1623e0d66acc954120557d5396bcf
hook 9d8ab2b296bb600efb12f1d98386350aef372d790447e45b7f5c15e15fb9462c
seen 8100  start 2677  end 2677  call 2677  harness_error 0  
differ 198  compared_of_seen 2677/8100
calls.jsonl 3f5066abfd47482ded7e895a2283b58e8d1ec9e58ab2b80842ba474cf9c7f51d
seen 8100 = compared 2677 + excluded 5423 (inner 5418: 2x2677 + 64 self-calls; module_call 4; other 1) + not concluded 0
start 2677 end 2677 call 2677 harness_error 0 differ 198
ok    seen = compared + excluded
ok    compared = start
ok    start = end + not concluded
ok    call = end
ok    inner = 2 x compared + self-calls (self-calls >= 0)
ok    no harness_error
ok    no call left unconcluded
ok    differences found (positive control)
```
Por dimensão: 176 diferenças de código de saída (2→3, inconclusive), 20 só de stdout (inclui o CLEAN plantado), 2 de stderr (inclui a recusa plantada).

## Os cinco itens
- [x] nulo: zero diferenças
- [x] positivo: as três dimensões acusadas
- [x] manifesto com hashes de referência, candidata, gancho e log
- [x] falha do harness é falha: 0 harness_error, 0 não concluídas, contas fechadas
- [x] provas ST01–ST03, cada uma mata o seu mutante
