# 0007 — Limiar de e-value inerte nos filtros

- **Status:** **Pendente** — defeito confirmado e coberto por teste; correção aguarda autorização
- **Data:** 2026-08-12
- **Decidido por:** — (em aberto)

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

**Em aberto.** Este ADR registra o defeito, seu alcance e um teste que o expõe. A correção
não foi aplicada porque altera comportamento científico, o que exige autorização explícita.

O teste [`tests/check_argv_numeric_comparison.py`](../../tests/check_argv_numeric_comparison.py)
**falha por projeto** enquanto o defeito existir. Ele é a evidência, não uma regressão.

## Consequências

- Enquanto pendente, o repositório contém um teste que falha. Isso é intencional e está
  declarado no docstring do próprio teste.
- Se a correção for aprovada, a migração para Python 3 ([K12](../known-issues.md)) fica mais
  segura: o mesmo padrão levantaria `TypeError` e quebraria a execução em vez de alterar
  resultados silenciosamente.
- Análises antigas feitas na rota DIAMOND usaram um limiar diferente do declarado. Reproduzi-las
  exige o comportamento antigo, o que reforça a necessidade de versionar a configuração
  junto ao resultado ([K6](../known-issues.md), [K9](../known-issues.md)).
