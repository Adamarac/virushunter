# 0019 — Ferramentas locais em `tools/`

- **Status:** Aceita (parcial — ver limites)
- **Data:** 2026-08-15
- **Decidido por:** Alan M

## Contexto

A [ADR-0018](0018-local-execution.md) fez a configuração descrever a execução local, mas
nenhuma ferramenta estava instalada. O pedido foi baixar executáveis e colocá-los numa
pasta `tools/`.

O ambiente da máquina, verificado antes de baixar qualquer coisa: Windows 11, Git Bash
(MSYS), com WSL/Debian, Docker, conda e rede disponíveis.

A restrição que decide tudo é a plataforma. A rota padrão precisa de **quatro** programas
(`blastx`, `bowtie2`, `diamond`, `dustmasker`), determinados por `snakemake -n -p` e não
por leitura da configuração — a lista completa de `tools:` tem 20 entradas, a maioria não
usada pelo `Snakefile`.

## Decisão

Baixar os builds oficiais para Windows em `tools/bin/`, e apontar `config/default.yaml`
para lá.

| Programa | Versão | Origem |
|---|---|---|
| `blastx`, `blastn`, `dustmasker`, `makeblastdb`, `blastdb_aliastool`, `blastdbcmd` | BLAST+ 2.17.0 | NCBI, `x64-win64` |
| `bowtie2`, `bowtie2-build`, `bowtie2-inspect` | 2.5.5 | GitHub, `mingw-x86_64` |
| `diamond` | 2.2.6 | GitHub, `diamond-windows` |

180 MB no total, extraindo só os executáveis de produção — sem as variantes `-debug` do
bowtie2 nem o resto da suíte BLAST+. **O projeto está dentro do OneDrive e tudo isto
sincroniza.** `tools/` foi para o `.gitignore`, com exceção do `README.md`: binário
versionado foi um dos problemas removidos no início desta refatoração, e repetir isso seria
desfazer uma decisão anterior.

`tools.scripts_dir` e os caminhos de ferramenta passaram a seguir uma regra única:
**nome simples é procurado no `PATH`; caminho com barra é relativo à raiz do projeto.**
Sem isso, um caminho relativo se resolveria contra a pasta da amostra, porque o Snakemake
roda com `--directory`.

`makeblastdb` era invocado como nome nu no `Snakefile`, fora da configuração. Passou a vir
de `tools:` como os demais.

### Dois obstáculos encontrados

**`blastx` e `blastn` não executavam.** Falhavam com
`error while loading shared libraries: nghttp2.dll`. O tarball do NCBI traz `nghttp2.dll` e
`ncbi-vdb-md.dll`, que não estavam na minha lista de extração. `dustmasker` e
`makeblastdb` funcionavam sem elas — testar só uma parte teria escondido o problema.

**`bowtie2-build` e `bowtie2-inspect` não executavam.** São scripts com
`#!/usr/bin/env python3`; no Windows o interpretador se chama `python`, e a ausência de
`python3` produzia uma mensagem enganosa da Microsoft Store sugerindo instalar Python — que
já estava instalado. `tools/bin/python3` é um redirecionamento de uma linha. Sem ele, o
índice do bowtie2 não pode ser construído.

## O que não foi possível

Estes **não têm build para Windows** — nem oficial, nem no bioconda, que publica apenas
`linux-64` e `osx-64` (verificado consultando o canal):

| Programa | Rota afetada |
|---|---|
| `cap3`, `SOAPdenovo-63mer`, `velveth`, `velvetg`, `meta-velvetg`, `abyss-pe` | `assembly.mode: "denovo"` |
| `hmmsearch` | rota `hmmer` (não migrada) |

| Rota | Roda com esta pasta? |
|---|---|
| padrão, paired-end, remoção de adaptador | **sim** |
| denovo | **não** |

Para a rota de montagem não existe download que resolva: exige WSL (o Debian já está nesta
máquina) ou Docker. É decisão de ambiente, e fica **em aberto** — as alternativas têm custos
diferentes (WSL compartilha o disco mas duplica o Python; Docker isola mas exige imagem) e
a escolha não é minha.

Deixei as chaves dessas ferramentas como nomes simples, e não como caminhos em `tools/`. A
falha então diz `hmmsearch: command not found`, que é a verdade, em vez de apontar um
arquivo ausente numa pasta que existe.

## Verificação

Não foi só `--version` — a lição vinha de `blastx`, que respondia vazio em vez de falhar
visivelmente:

| Teste | Resultado |
|---|---|
| `diamond makedb` + `blastx --evalue 0.01 --threads 2 --outfmt 6` | linha `.m8` válida, com `VIRUS_` na coluna 2 — o formato que `diamond_filter_NR.py` consome |
| `bowtie2-build` + `bowtie2` sobre referência de DNA | SAM válido, 100% de alinhamento, CIGAR `42M` |
| `makeblastdb -dbtype prot` + `blastx` com **as flags exatas** da regra `blast_virus` | XML com 1 hit, `<Hsp_evalue>7.82159e-28` |
| `makeblastdb -dbtype nucl -parse_seqids` | ok |
| `dustmasker -infmt fasta -outfmt fasta` | ok |
| As 6 rotas do DAG | 349 / 355 / 357 / 369 / 445 / 349 — inalteradas |

O primeiro teste do bowtie2 deu 0% de alinhamento porque eu indexei proteína e alinhei DNA.
Erro do teste, não da ferramenta; refeito corretamente.

## Consequências

- Duas questões que estavam marcadas como *não verificado* agora têm resposta:
  - **Padrão do `--evalue` do DIAMOND: 0.001**, dez vezes mais restritivo que o `0.01`
    configurado. Resolve a pendência da [ADR-0007](0007-inert-evalue-threshold.md) e
    quantifica o efeito da correção.
  - **[K26](../known-issues.md) — `-max_target_seqs 1` não devolve o melhor hit.** A
    ferramenta avisa. Afeta as duas rotas do filtro NR. Registrada, não corrigida:
    consertar muda o resultado de todas as buscas.
- **Deriva de versão.** O pipeline foi publicado com BLAST 2.2.31 e DIAMOND 0.7.x; aqui
  estão 2.17.0 e 2.2.6. Um banco DIAMOND de 2015 não é legível pela 2.2.6 — os bancos
  precisam ser reconstruídos. Reproduzir análises antigas *bit a bit* deixa de ser possível
  com estas versões, e a referência congelada em `tests/reference/` (removida) documentava o
  comportamento do orquestrador, não o das ferramentas.
- **Os bancos de dados continuam ausentes**, e são obrigatórios. Nenhuma rota roda até o
  fim. É o próximo bloqueio, e é grande: o NR completo passa de 100 GB.
- Nada do pipeline foi executado de ponta a ponta. Continua valendo a
  [ADR-0009](0009-no-execution-environment.md).
