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
| `steps.hmmer` | `hmmsearch` não tem build para Windows; scripts no histórico |
| `steps.clark` | CLARK não está instalado nem tem chave em `tools:` |
| `steps.nt_route` | scripts no histórico; carrega o [K2](known-issues.md), contagens não confiáveis |
| `steps.reassemble` | 415 linhas em Python 2 no histórico, mais os montadores ausentes |
| `steps.merge_pairs` | FLASH ausente, e sem chave em `tools:` |
| `steps.input.from_bam` | `samtools`/`picard` sem build para Windows |
| `steps.input.sra_prep` | SRA toolkit ausente |
| `steps.mystery` | as regras de merge rodam sempre — era assim no original também |
| `steps.host_filter.keep_*` | o filtro roda sempre; falta a variante |
| `steps.viral_search.phage` | falta a variante com o banco de fagos |
| `steps.output.*` | publicação e cópia rodam sempre |

Os scripts removidos continuam recuperáveis:

```sh
git show 6961916^:script/hmmer_annot.py
```

Mas recuperá-los não devolve rotas prontas: boa parte é Python 2 e precisaria da mesma
migração que a rota principal recebeu.

## Limite de verificação

Nenhuma dessas rotas foi **executada** — faltam ferramentas e bancos
([ADR-0009](decisions/0009-no-execution-environment.md)). O que se verifica é que o grafo
resolve e que os comandos gerados são os esperados.

A referência congelada que validava a rota principal foi removida, e recapturá-la exigiria
rodar o gerador antigo. Isso está bloqueado localmente: ele dispara 21 `ssh` em paralelo
escrevendo no mesmo arquivo, o que o Windows não permite. Com o Docker Desktop ligado, ou
com `python3` instalado no WSL, o procedimento original volta a funcionar.
