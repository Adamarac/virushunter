# 0005 — Estratégia do filtro contra NR

- **Status:** Aceita
- **Data:** 2026-08-15 (registrada como pendente em 2026-08-12)
- **Decidido por:** Alan M

## Contexto

[ADR-0004](0004-virus-hunter-as-reference.md) fixou `virus_hunter.py` como referência
científica, mas deixou explicitamente de fora a escolha do filtro contra NR. Esta ADR
registra essa questão em separado, porque é uma decisão científica independente da escolha
do orquestrador.

O filtro NR é a defesa central contra falso positivo: um contig que se parece com vírus
mas se parece **ainda mais** com algo não-viral não deveria ser reportado como vírus. Duas
implementações coexistem no repositório, e elas aplicam critérios diferentes.

### Rota A — comparação de e-values (`blast_filter_NR.py`)

[`blast_filter_NR.py:138-139`](../../script/search/filter_nr.py):

```python
if nrE.has_key(query) and virusE.has_key(query) and float(hsp.expect) >= nrE[query]:
    filter+=1; continue   # descarta
```

O hit viral só passa se seu e-value for **melhor** que o do melhor hit não-viral. O valor
não-viral é preservado na saída como `LNVNRE` (*lowest non-virus NR e-value*), o que
permite ao revisor humano julgar cada hit.

A rota também exclui do conjunto "não-viral" qualquer subject que já esteja no banco viral
ou cujo título contenha `VIRUS`/`VIRAL`
([linhas 55-62](../../script/search/filter_nr.py)), evitando que um hit viral seja
usado contra si mesmo.

### Rota B — lista negra por prefixo (`diamond_filter_NR.py`)

[`diamond_filter_NR.py:46-57`](../../script/search/filter_nr.py):

```python
subject=subject.strip().split('_', 1)[0]
if subject != "VIRUS":
    nrE.add(query)        # entra na lista negra
```

Qualquer query cujo melhor hit DIAMOND não tenha o prefixo `VIRUS_` é descartada, **sem
comparar magnitudes**. O campo `LNVNRE` da saída é preenchido com `'-'`
([linha 116](../../script/search/filter_nr.py)) — a informação que permitiria
revisão humana é perdida.

### Situação no código

A rota B é a ativa. A rota A está **comentada** em
`virus_hunter.py:2208`:

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

**Tornar o método selecionável**, em vez de escolher um dos dois em nome do grupo.

```yaml
steps:
  nr_filter_method: "diamond"   # ou "blast"
```

O padrão é `diamond`, que **preserva exatamente o comportamento da referência**: quem não
mexer na configuração continua obtendo o mesmo resultado de antes. A rota A deixa de estar
comentada e passa a ser alcançável por configuração.

Razão para não decidir pelo grupo: as três evidências que resolveriam a questão
(listadas abaixo) são todas empíricas e nenhuma está disponível — não há registro da época,
não há ambiente de execução ([ADR-0009](0009-no-execution-environment.md)) e não há dados
para comparar as rotas. Escolher agora seria fixar por decreto uma questão científica que
pertence a quem tem os dados. Deixar selecionável permite que a comparação quantitativa —
a evidência nº 3 — seja finalmente feita.

### Como está implementado

Cada método define suas próprias regras no `Snakefile`, sem ramificação dentro das regras:

| | `diamond` (padrão) | `blast` |
|---|---|---|
| Busca contra NR | `diamond blastx --outfmt 6`, uma vez por amostra | `blastx -outfmt 5`, uma vez por amostra **e por fatia** |
| Filtro | `diamond_filter_NR.py` | `blast_filter_NR.py` |
| Critério | prefixo do melhor hit | comparação de e-values |
| `LNVNRE` no relatório | `-` | valor real |
| Tarefas no DAG (fixture de 2 amostras) | 349 | 445 |

A diferença de 96 tarefas se explica inteira: −2 `diamond_nr`, −2 `merge_significant`,
+100 `blastx_nr`. O método `blast` **não produz** o arquivo concatenado
`fastq/{sample}_sig`, porque consome as fatias `_s` individualmente — igual ao original,
onde `blast_nr_filter.sh` usava `sigfaname` por fatia e o `_sig` concatenado existia
apenas para alimentar o DIAMOND.

A rota `blast` é reproduzida a partir da linha
`virus_hunter.py:1767-1769`, com as mesmas
flags. Note que o `blastx` contra o NR **não** leva `-db_soft_mask`, diferente do `blastx`
viral, que leva `-db_soft_mask 21`. Isso foi preservado como está no original; *não
determinado* se é intencional.

### Limites desta decisão

- A rota `blast` **nunca foi executada**, nem antes nem agora: ela estava comentada no
  orquestrador e aqui foi validada apenas por resolução de DAG. Que o grafo feche não
  garante que `blast_filter_NR.py` funcione sobre entradas reais.
- A rota híbrida descrita nas alternativas **não** foi implementada. Ela continua sendo a
  opção mais promissora, e agora é comparável contra as outras duas.
- `blast_filter_NR.py` segue no repositório, agora por uso e não por precaução.

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
