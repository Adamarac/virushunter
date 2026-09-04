# tests/ — dados para verificar o fluxo

Não há testes automatizados: foram removidos a pedido. O que resta aqui são os dados
mínimos para conferir **à mão** que o workflow ainda resolve.

```
fixture/fastq/   4 FASTQ + samples.txt, com a convencao de nomes do sequenciador
```

## Como verificar

```sh
export PYTHONPATH=src
snakemake -n -s workflow/Snakefile --directory tests/fixture
snakemake -n -s workflow/Snakefile --directory tests/fixture --config routes=paired-end
```

O número de tarefas de cada rota deve ser:

| Rota | Tarefas |
|---|---|
| padrão | 349 |
| `paired-end` | 355 |
| `adaptor` | 357 |
| `denovo` | 369 |
| `nucleotide` | 349 |
| `diamond` | 449 |
| `fasta-input` | 349 |
| `no-dedup` | 349 |
| `nr-filter-blast` | 445 |
| `config/cluster-legacy.yaml` | 349 |

As rotas estão em `config/routes/` e se escolhem com `--config routes=<nome>`.
Ver [docs/routes.md](../docs/routes.md).

**Nada guarda esses números automaticamente.** Quem mexer no `Snakefile` precisa rodar as
seis à mão.

## O conteúdo dos FASTQ não importa

A descoberta de amostras lê apenas os **nomes** dos arquivos. Os quatro FASTQ têm duas
leituras sintéticas cada, só para não serem vazios. `samples.txt` lista os nomes com `.gz`
porque era assim que o orquestrador antigo os recebia.

## O que existia aqui antes

Quatro diretórios `expected*/` com 246 arquivos: os scripts shell que `virus_hunter.py`
gerava, congelados como especificação executável durante a migração para Python 3.

Foram removidos porque deixaram de ter função:

- `virus_hunter.py` foi apagado ([ADR-0020](../docs/decisions/0020-prune-to-the-migrated-version.md)),
  então **não podiam mais ser regerados**.
- `capture.sh`, `verify.sh` e `compare_normalized.sh` foram removidos antes, então **nada
  os lia**.
- 204 dos 246 descreviam um cluster que não existe — `ssh bsidna4`, `/mnt/cluster/xdeng/`,
  BLAST 2.2.31.

Continuam no histórico:

```sh
git show 90ea851:tests/reference/expected/blast_adaptor.sh
git show 2705fa7:tests/reference/expected/clonetrim.sh   # captura original em Python 2
```

Vale saber o que se perdeu: eram a descrição mais precisa que existia do que o pipeline
original fazia, comando a comando. O `Snakefile` foi escrito contra elas, então essa
informação está no workflow — mas não mais numa forma que se possa comparar.
