# Rotas do pipeline

O pipeline tem variantes. Cada uma é um arquivo em `config/routes/`, e se escolhe pelo
nome:

```sh
snakemake -s workflow/Snakefile --config routes=denovo
snakemake -s workflow/Snakefile --config routes=denovo,contigs-only
```

Várias rotas se combinam separando por vírgula, na ordem — a última vence nas chaves que
ela define.

## Rotas disponíveis

| Nome | O que muda | Tarefas |
|---|---|---|
| *(nenhuma)* | padrão: blastx contra proteínas virais, sem montagem | 349 |
| `paired-end` | usa as duas leituras de cada par | 355 |
| `adaptor` | remove adaptador por blastn e apara por qualidade | 357 |
| `denovo` | montagem por três programas mais consenso | 369 |
| `nucleotide` | busca comparando DNA em vez de proteína | 349 |
| `diamond` | busca pelo DIAMOND, muito mais rápido que o blastx | 449 |
| `fasta-input` | entrada em FASTA, convertida para FASTQ antes | 349 |
| `no-dedup` | sem remoção de duplicatas de PCR | 349 |
| `nr-filter-blast` | filtro NR por comparação de e-values | 445 |
| `contigs-only` | só os contigs vão à busca; use com `denovo` | — |
| `phage` | busca contra o banco de fagos | 349 |
| `remove-bacteria` | descarta bactérias e mantém o humano | 401 |
| `remove-both` | descarta humano e bactérias | 403 |
| `clark` | classificação taxonômica pelo CLARK | 361 |
| `nt` | contagem por taxon contra o banco nt — [K2](known-issues.md), contagens não confiáveis | 381 |

`clark` e `nt` **não podem ser combinadas**: escrevem a mesma contagem por taxon. No
gerador antigo uma sobrescrevia a outra em silêncio; aqui o workflow recusa com uma
mensagem.

Rotas com o mesmo número de tarefas mudam **os comandos**, não a forma do grafo.
`fasta-input` só tem efeito quando a entrada é de fato FASTA.

## Por que `--config routes=` e não vários `--configfile`

Porque **vários `--configfile` não se combinam**. O Snakemake substitui a seção inteira em
vez de fundir:

```sh
# ERRADO: perde assembly.mode do denovo, em silêncio
snakemake --configfile config/routes/denovo.yaml --configfile config/routes/contigs-only.yaml
```

Verificado: nessa forma o pipeline enxerga apenas `{"skip_reads": true}` — a montagem
some sem aviso. `--config routes=` usa a fusão profunda do próprio pacote
(`virushunter.config.merge`), que só sobrescreve as chaves que a rota define.

## Chaves que ainda não existem no workflow

Estas continuam em `config/default.yaml` porque descrevem capacidades do pipeline
original, mas **não foram migradas**. Mudar qualquer uma delas faz o workflow **parar com
erro**, em vez de ignorar em silêncio:

| Chave | O que falta |
|---|---|
| `steps.hmmer` | **a rota nunca funcionou** — o gerador manda executar 7 arquivos que ele mesmo não cria, e o passo que roda o HMMER não é executado. Ver [K34](known-issues.md) |
| `steps.reassemble` | 415 linhas em Python 2 no histórico, mais os montadores ausentes |
| `steps.merge_pairs` | FLASH ausente, e sem chave em `tools:` |
| `steps.input.from_bam` | `samtools`/`picard` sem build para Windows |
| `steps.input.sra_prep` | SRA toolkit ausente |

Os scripts removidos continuam recuperáveis:

```sh
git show 6961916^:script/hmmer_annot.py
```

Mas recuperá-los não devolve rotas prontas: boa parte é Python 2 e precisaria da mesma
migração que a rota principal recebeu.

## Como as rotas são verificadas

Nenhuma foi **executada** — faltam ferramentas e bancos
([ADR-0009](decisions/0009-no-execution-environment.md)). Mas os comandos que cada rota
gera são conferidos contra o comportamento do gerador original, com
`tests/capture-reference.sh`, que roda o `virus_hunter.py` recuperado do histórico dentro
de um container.

Esse procedimento foi validado: a recaptura da rota padrão sai **idêntica, byte a byte**,
aos 56 arquivos da referência congelada que existia em `tests/reference/expected/`.

O que a comparação com a referência revelou, rota a rota:

| Rota | Confirmado contra a referência |
|---|---|
| `nucleotide` | comando `blastn` idêntico, com `-db_soft_mask 11` e o banco de DNA |
| `phage` | só troca o banco para `phage_mask` |
| `diamond` | `diamond blastx --sensitive` produzindo `.pre`, depois o conserto do XML |
| `no-dedup` | o `.dup` **não é produzido**: o estágio seguinte lê o `.fil` direto |
| `remove-bacteria` | 27 índices e a faixa `1 27` passada ao `host_mask.py` |
| `clark` | `-k 20 -n 48 -T target{i}.txt -D CLARK_DB{i}/`, três bancos, mesma ordem de argumentos |
| `nt` | 14 índices e `nt_counts.py <amostra> . report 1 14` |

A checagem do `no-dedup` corrigiu a minha primeira implementação, que fazia uma cópia
`.fil` → `.dup`. A referência simplesmente pula a etapa.
