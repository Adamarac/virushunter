# 0016 — Workflow em Snakemake

- **Status:** Aceita (primeira fatia; rotas opcionais pendentes)
- **Data:** 2026-08-13
- **Decidido por:** Alan M

## Contexto

O `script/virus_hunter.py` compila a configuração em ~50 scripts shell e os despacha por
SSH para 20 nós de cluster ([`architecture.md`](../architecture.md)). Ele é gerador, não
executor: não há grafo de dependências, retomada, nem detecção de falha — `schedule2.py`
decide que um job terminou olhando se o arquivo de saída existe e não está vazio
([K5](../known-issues.md)).

**A execução passou a ser local.** Isso muda a natureza do trabalho: o envelope de
distribuição não precisa ser traduzido, precisa **desaparecer**. Os 20 nós, o SSH, o
`job%nservers`, o `schedule2.py`, a senha de `sudo` e o `chmod 777` não têm função local.

## Alternativas consideradas

**Manter o gerador e só corrigi-lo.** Preserva a referência byte a byte como teste de
regressão. Descartada: mantém ausência de DAG, de retomada e de detecção de falha, que são
justamente os problemas.

**Nextflow.** Já experimentado pelo grupo. Descartado a favor do Snakemake, que foi a
escolha registrada — sintaxe Python, o mesmo idioma do resto do projeto.

**Snakemake.** Dependências pelo grafo de arquivos, paralelismo local por `--cores`,
retomada nativa, e falha real quando um comando retorna erro.

## Decisão

`workflow/Snakefile` com 17 regras cobrindo a **configuração de referência**: single-end,
sem montagem, sem remoção de adaptador, filtro NR por DIAMOND.

A especificação de cada regra é a referência capturada em `tests/reference/expected/` — os
comandos reais do pipeline original, com seus parâmetros. Onde uma regra diverge, há
comentário dizendo por quê.

Os helpers testáveis ficam em `virushunter.workflow`, não dentro do Snakefile: arquivos
Snakemake são difíceis de testar, e a descoberta de amostras é exatamente o tipo de coisa
que falha em silêncio.

### O que melhorou sem ser pedido

**Descoberta de amostras.** O `readSeeds2()` fazia
`line.split('.')[0].split('_')[1]` — posicional, e qualquer nome fora da convenção do
sequenciador era agrupado errado sem aviso. Agora os padrões são explícitos e um arquivo
não reconhecido é **reportado**, não ignorado.

**Ordem determinística.** Amostras vêm ordenadas. A ordem de iteração antes vinha do hash
de dicionário do Python 2 e decidia atribuição de nó e ordem de agregação — foi a origem da
[ADR-0010](0010-dict-ordering-behaviour-change.md).

**Dependências explícitas.** No original, `combineContig_reads` fazia `cat <sample>_contig4
<sample>.fa`, e com `assembly.mode="no"` o `_contig4` nunca existia — o comando seguia
adiante por tolerância do `cat`. Aqui a dependência é declarada, e o que não existe não é
pedido.

### Validação

`snakemake -n` resolve o grafo inteiro sem executar ferramenta nenhuma — não precisa de
BLAST, bowtie2 nem bancos, que é o único motivo de isso ser testável
([ADR-0009](0009-no-execution-environment.md)).

[`tests/test_workflow_dag.sh`](../../tests/test_workflow_dag.sh) exige cardinalidade
exata: 326 jobs, com 100 de `blast_virus` (2 amostras × 50 fatias). Verificado nos dois
sentidos — apontar uma regra para um arquivo que ninguém produz faz o teste falhar com
saída 1.

## Consequências

- O pipeline ganha DAG, retomada e falha real. [K5](../known-issues.md) deixa de existir
  nesta rota: um comando que retorna erro para o workflow.
- **A referência deixa de ser teste de regressão.** Não há mais scripts shell gerados para
  comparar. Ela continua sendo a especificação mais precisa do que o pipeline faz, e é
  contra ela que as regras foram escritas — mas a proteção byte a byte acabou. É o custo da
  escolha do Snakemake, e estava previsto.
- **Rotas não migradas:** montagem `denovo` (a configuração que o método publicado exige,
  [ADR-0004](0004-virus-hunter-as-reference.md)), CLARK, rota NT, HMMER/vFam, reAssemble,
  remoção de adaptador, paired-end, e toda a etapa de relatório HTML.
- **`--evalue` do DIAMOND reproduzido como está**, sem a correção que a
  [ADR-0007](0007-inert-evalue-threshold.md) deixou pendente. A regra codifica o
  comportamento atual; mudá-lo continua sendo decisão sua.
- O gerador legado **permanece** e continua coberto por `verify.sh`. Remover é decisão para
  quando o workflow cobrir as rotas que importam.
