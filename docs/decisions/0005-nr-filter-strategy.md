# 0005 — Estratégia do filtro contra NR

- **Status:** **Pendente**
- **Data:** 2026-08-12
- **Decidido por:** — (em aberto)

## Contexto

[ADR-0004](0004-virus-hunter-as-reference.md) fixou `virus_hunter.py` como referência
científica, mas deixou explicitamente de fora a escolha do filtro contra NR. Esta ADR
registra essa questão em separado, porque é uma decisão científica independente da escolha
do orquestrador.

O filtro NR é a defesa central contra falso positivo: um contig que se parece com vírus
mas se parece **ainda mais** com algo não-viral não deveria ser reportado como vírus. Duas
implementações coexistem no repositório, e elas aplicam critérios diferentes.

### Rota A — comparação de e-values (`blast_filter_NR.py`)

[`blast_filter_NR.py:138-139`](../../script/blast_filter_NR.py#L138-L139):

```python
if nrE.has_key(query) and virusE.has_key(query) and float(hsp.expect) >= nrE[query]:
    filter+=1; continue   # descarta
```

O hit viral só passa se seu e-value for **melhor** que o do melhor hit não-viral. O valor
não-viral é preservado na saída como `LNVNRE` (*lowest non-virus NR e-value*), o que
permite ao revisor humano julgar cada hit.

A rota também exclui do conjunto "não-viral" qualquer subject que já esteja no banco viral
ou cujo título contenha `VIRUS`/`VIRAL`
([linhas 55-62](../../script/blast_filter_NR.py#L55-L62)), evitando que um hit viral seja
usado contra si mesmo.

### Rota B — lista negra por prefixo (`diamond_filter_NR.py`)

[`diamond_filter_NR.py:46-57`](../../script/diamond_filter_NR.py#L46-L57):

```python
subject=subject.strip().split('_', 1)[0]
if subject != "VIRUS":
    nrE.add(query)        # entra na lista negra
```

Qualquer query cujo melhor hit DIAMOND não tenha o prefixo `VIRUS_` é descartada, **sem
comparar magnitudes**. O campo `LNVNRE` da saída é preenchido com `'-'`
([linha 116](../../script/diamond_filter_NR.py#L116)) — a informação que permitiria
revisão humana é perdida.

### Situação no código

A rota B é a ativa. A rota A está **comentada** em
[`virus_hunter.py:2208`](../../script/virus_hunter.py#L2208):

```python
#sf.write('source blast_nr_filter.sh >blastnr.log  \nwait\n')
sf.write('source diamond_nr_filter.sh >diamondnr.log  \nwait\n')
```

Ou seja: o orquestrador adotado como referência usa o critério **mais fraco**, e o mais
forte foi desativado sem registro do motivo.

## Alternativas consideradas

**Manter a rota B (DIAMOND, lista negra).** É o comportamento efetivamente ativo na
referência, e DIAMOND é ordens de magnitude mais rápido que blastx — provavelmente o motivo
da troca (*hipótese*: nenhuma justificativa foi registrada). Custo: critério binário, perda
do `LNVNRE`, e maior chance de descartar vírus verdadeiros cujo melhor hit no NR seja um
não-viral fracamente similar.

**Voltar à rota A (BLAST, comparação de e-values).** Critério estatisticamente defensável
e preserva informação para revisão. Custo: blastx contra o NR é caro, e foi justamente o
gargalo que motivou a adoção do DIAMOND.

**Rota híbrida.** Usar DIAMOND pela velocidade, mas aplicar comparação de e-values sobre a
saída `.m8` em vez de lista negra — o formato `.m8` traz o e-value na coluna 11, então a
informação necessária **já está disponível** e é descartada. Preserva a velocidade e
recupera o critério e o `LNVNRE`. *Não verificado:* exigiria confirmar que o banco DIAMOND
tem cobertura equivalente à do NR usado pela rota A.

## Decisão

**Em aberto.**

Enquanto pendente: não alterar nenhum dos dois filtros, e não remover
`blast_filter_NR.py`.

Nota: ambos os filtros são afetados por [K1](../known-issues.md) — o limiar de e-value
inerte por comparação `float < str`. Essa correção é independente desta decisão e deve ser
tratada antes, pois muda a linha de base de qualquer comparação entre as rotas.

## Evidências que resolveriam a questão

1. Qual filtro foi usado nas análises publicadas ou em produção pelo grupo.
2. Se a troca para DIAMOND foi por desempenho ou por critério científico. Um `run.log` ou
   qualquer registro da época responderia.
3. Uma comparação quantitativa sobre o mesmo conjunto de dados: quantos hits cada rota
   deixa passar e barra, e onde discordam. Requer a infraestrutura de validação proposta
   em [`known-issues.md`](../known-issues.md).
