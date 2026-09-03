# tools/ — executáveis das ferramentas externas

Esta pasta contém os programas que o pipeline chama. Ela **não é versionada**
(`.gitignore`), porque binário em repositório de código foi justamente um dos problemas
removidos no início desta refatoração.

O `config/default.yaml` já aponta para cá. Nada precisa entrar no `PATH`.

## O que está aqui

| Programa | Versão | Origem |
|---|---|---|
| `blastx`, `blastn`, `dustmasker`, `makeblastdb` | BLAST+ 2.17.0 | NCBI, build oficial `x64-win64` |
| `bowtie2`, `bowtie2-build`, `bowtie2-inspect` | 2.5.5 | GitHub, build oficial `mingw-x86_64` |
| `diamond.exe` | 2.2.6 | GitHub, build oficial `diamond-windows` |
| `python3` | — | atalho de uma linha, ver abaixo |

Só os executáveis de produção foram extraídos. As variantes `-debug` do bowtie2 e o resto
da suíte BLAST+ ficaram de fora para não encher a pasta (o projeto está dentro do
OneDrive, e tudo aqui sincroniza).

### O atalho `python3`

`bowtie2-build` e `bowtie2-inspect` são scripts com `#!/usr/bin/env python3`. No Windows o
interpretador se chama `python`, e sem `python3` no `PATH` os dois falham com uma mensagem
enganosa da Microsoft Store. O arquivo `python3` aqui é um script de uma linha que
redireciona. Sem ele, o índice do bowtie2 não pode ser construído.

## O que **não** está aqui, e por quê

Estes programas **não têm build para Windows** — nem oficial, nem no bioconda, que publica
apenas `linux-64` e `osx-64` (verificado):

| Programa | Para que serve | Rota afetada |
|---|---|---|
| `cap3` | consenso final da montagem | `assembly.mode: "denovo"` |
| `SOAPdenovo-63mer` | montagem | `assembly.mode: "denovo"` |
| `velveth`, `velvetg`, `meta-velvetg` | montagem | `assembly.mode: "denovo"` |
| `abyss-pe` | montagem | `assembly.mode: "denovo"` |
| `hmmsearch` | busca por famílias virais | rota `hmmer` (não migrada) |

### Consequência prática

| Rota | Roda no Windows com esta pasta? |
|---|---|
| padrão (`assembly.mode: "no"`) | **sim** |
| paired-end | **sim** |
| remoção de adaptador | **sim** |
| denovo (montagem) | **não** — faltam os 6 montadores |

Para a rota de montagem não há download que resolva: é preciso WSL (o Debian já está
instalado nesta máquina) ou Docker, onde os binários Linux funcionam. Essa é uma decisão
de ambiente, não de configuração, e está em aberto.

## Bancos de dados

**Não estão aqui e não vêm com o projeto.** Veja `databases:` no
`config/default.yaml`: o pipeline espera uma pasta `db/` no diretório de trabalho. Sem os
bancos, nenhuma rota roda até o fim, mesmo com todas as ferramentas presentes.

Atenção à versão: um banco DIAMOND criado com a v0.7.x de 2015 **não é legível** pela
v2.2.6 instalada aqui. Os bancos precisam ser reconstruídos com estas versões.

## Como refazer esta pasta

Os três downloads, sem nenhuma etapa manual:

```sh
mkdir -p tools/bin && cd /tmp
curl -LO "https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/ncbi-blast-2.17.0+-x64-win64.tar.gz"
curl -LO "https://github.com/BenLangmead/bowtie2/releases/download/v2.5.5/bowtie2-2.5.5-mingw-x86_64.zip"
curl -LO "https://github.com/bbuchfink/diamond/releases/download/v2.2.6/diamond-windows.zip"
```

Depois extraia para `tools/bin/` apenas `blastx`, `blastn`, `dustmasker` e `makeblastdb`
do BLAST+; `bowtie2`, `bowtie2-align-{s,l}`, `bowtie2-build{,-s,-l}` e
`bowtie2-inspect{,-s,-l}` do bowtie2; e `diamond.exe`. Recrie o atalho `python3`.

## O que foi testado

Não foi só `--version`. Cada ferramenta rodou de verdade:

- `diamond makedb` + `diamond blastx --evalue 0.01 --threads 2 --outfmt 6` sobre uma
  proteína e uma leitura sintéticas → linha `.m8` válida, no formato que
  `diamond_filter_NR.py` consome.
- `bowtie2-build` + `bowtie2` sobre uma referência de DNA → SAM válido, 100% de
  alinhamento, CIGAR `42M`.
- BLAST+: ver a seção de verificação na [ADR-0019](../docs/decisions/0019-local-tools.md).

O pipeline completo **não** foi executado: faltam os bancos de dados.
