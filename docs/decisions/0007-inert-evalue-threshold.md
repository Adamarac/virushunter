# 0007 — Limiar de e-value inerte nos filtros

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

Os filtros contra NR fazem:

```python
E_VALUE_THRESH = sys.argv[5]             # string, ex. '0.01'
...
if float(hsp.expect) < E_VALUE_THRESH:   # float < str
```

`sys.argv` sempre entrega strings. Em Python 2, comparar número com string não levanta
erro: a linguagem recorre a uma ordenação artificial em que todo valor numérico é menor
que qualquer string. **A condição é sempre verdadeira** — o limiar declarado nunca é
aplicado.

Em Python 3 o mesmo código levantaria `TypeError`, e é por isso que o defeito sobreviveu
sem ser notado.

### Alcance

Varredura dos 155 arquivos `.py` com
[`tests/check_argv_numeric_comparison.py`](../../tests/check_argv_numeric_comparison.py):

| Arquivo | Linha | Alcançável pelo pipeline de referência |
|---|---|---|
| [`diamond_filter_NR.py`](../../script/diamond_filter_NR.py#L94) | 94 | **Sim — é o filtro ativo** |
| [`blast_filter_NR.py`](../../script/blast_filter_NR.py#L132) | 132 | Sim (rota alternativa, ver [ADR-0005](0005-nr-filter-strategy.md)) |
| [`diamond_filter.py`](../../script/diamond_filter.py#L125) | 125 | Não |

Nenhum outro arquivo apresenta o padrão. Quatro falsos positivos da primeira versão do
verificador foram eliminados (HTML em string tripla; nomes convertidos no ponto de chamada,
como `int(illumina)` em `trim_quality.py`).

### Impacto real — mais estreito do que parece

O mesmo `EVALUE` alimenta **tanto** o `-evalue` do BLAST a montante **quanto** o limiar do
filtro ([`virus_hunter.py:1804-1806`](../../script/virus_hunter.py#L1804-L1806)). Como o
XML já chega contendo apenas hits com e-value ≤ `EVALUE`, o filtro inerte não deixa passar
nada que o BLAST já não tivesse aprovado.

Consequência: **na rota padrão (blastx), corrigir o defeito praticamente não muda a saída** —
apenas hits com e-value exatamente igual a `EVALUE` passariam a ser excluídos, por causa da
comparação estrita `<`.

Onde o defeito realmente morde:

1. **Rota DIAMOND** (`doDiamondOnly`). A chamada em
   [`virus_hunter.py:1801`](../../script/virus_hunter.py#L1801) **não passa `--evalue`**,
   usando o padrão da ferramenta. Com o filtro inerte, o limiar efetivo passa a ser o
   padrão do DIAMOND, e não o `EVALUE` configurado. Ajustar `EVALUE` nessa rota não produz
   o efeito esperado. *Não verificado:* o valor padrão exato da versão de DIAMOND instalada
   — confirmar com `diamond blastx --help` no ambiente de execução.
2. **Endurecer o limiar do filtro isoladamente é impossível**, e falha em silêncio.
3. Qualquer separação futura entre o e-value da busca e o do filtro reintroduz o problema.

## Alternativas consideradas

**Corrigir para `float(sys.argv[5])`.** Uma palavra em cada arquivo. Restaura o
comportamento declarado. Custo: é alteração de comportamento científico, ainda que
estreita — muda a saída no limite exato e na rota DIAMOND.

**Corrigir e passar `--evalue` explicitamente ao DIAMOND.** Fecha também a divergência da
rota 1. Custo: duas mudanças científicas em vez de uma, e a rota DIAMOND está desligada na
configuração de referência.

**Não corrigir; apenas documentar.** Preserva exatamente o comportamento histórico, o que
tem valor para reproduzir análises antigas. Custo: mantém um parâmetro que mente.

## Decisão

Converter no ponto de ligação, nos três arquivos:

```python
E_VALUE_THRESH = float(sys.argv[5])
```

Escolhida a alternativa mínima. **Não** se acrescentou `--evalue` às chamadas DIAMOND: isso
é uma segunda mudança científica, com alcance próprio (afeta também a busca NR da rota
ativa, cujo `.m8` determina a lista negra), e merece decisão separada. Fica registrada como
pendência abaixo.

A conversão é **estrita, sem tratamento de exceção**. Um argumento não numérico passa a
falhar alto. Envolvê-la em `try/except` perpetuaria exatamente o padrão que torna este
projeto difícil de confiar: erro silencioso disfarçado de sucesso.

## Consequências

- O limiar declarado passa a ser aplicado de fato. Na rota padrão blastx a saída muda
  apenas no limite exato (`<` estrito); na rota DIAMOND o `EVALUE` configurado passa a
  governar de verdade.
- A migração para Python 3 ([K12](../known-issues.md)) fica mais segura: o padrão corrigido
  não depende mais da ordenação artificial do Python 2.

### Efeito sobre os orquestradores legados — divulgação

A verificação dos pontos de chamada revelou um defeito preexistente. Apenas o orquestrador
de referência passa o e-value nessa posição:

| Orquestrador | `argv[5]` recebe |
|---|---|
| [`virus_hunter.py:1825`](../../script/virus_hunter.py#L1825) — referência | `EVALUE` ✓ |
| `readseeds2.py:792` — legado | **`hsp`** (`'NO'`) |
| `readseeds_denovo.py:713` — legado | **`hsp`** |
| `readseeds_cloud.py:416` — legado | **`hsp`** |
| `readseeds.py:166` — legado | só 3 argumentos |

Nos legados, `'NO'` era usado como limiar — comparação sempre verdadeira, filtro inerte,
sem erro. E como `argv[6]` não existia, `hsp_only` caía no `except` e virava `'NO'`. Os
dois parâmetros estavam errados.

Depois desta correção, `float('NO')` levanta `ValueError` e esses orquestradores **falham
alto**. Isso é o resultado desejado — o defeito era real e estava oculto — mas é uma
mudança de comportamento para eles, e está registrada como
[K24](../known-issues.md). Eles já são legado por [ADR-0004](0004-virus-hunter-as-reference.md).

Isso também **corrobora a ADR-0004**: a assinatura de `blast_filter_NR.py` foi atualizada
junto com `virus_hunter.py`, e os demais nunca acompanharam — o que é esperado se
`virus_hunter.py` era o orquestrador em manutenção ativa.

### Pendências abertas por esta ADR

1. **`--evalue` explícito nas chamadas DIAMOND.** A busca viral
   ([`virus_hunter.py:1801`](../../script/virus_hunter.py#L1801)) e a busca NR
   ([`:1848`](../../script/virus_hunter.py#L1848)) não passam `--evalue`, usando o padrão da
   ferramenta. *Não verificado:* o valor padrão da versão instalada — confirmar com
   `diamond blastx --help` no ambiente de execução.
2. **Análises antigas na rota DIAMOND** usaram um limiar diferente do declarado.
   Reproduzi-las exige o comportamento anterior, o que reforça a necessidade de versionar
   configuração junto ao resultado ([K6](../known-issues.md), [K9](../known-issues.md)).
