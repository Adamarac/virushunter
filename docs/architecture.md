# Arquitetura atual

Complementa [`pipeline.md`](pipeline.md) (o que roda, em que ordem) e
[`invariants.md`](invariants.md) (os contratos implícitos). Aqui: como o software está
organizado, e por que está difícil de mudar.

---

## Três camadas

O projeto não tem pacotes. `script/` é um diretório plano com cerca de 200 arquivos, e
**nenhum arquivo Python importa outro**. Ainda assim, existe uma estrutura clara em três
camadas, acopladas por linha de comando e por arquivos em disco.

```
┌─────────────────────────────────────────────────────────────┐
│ CAMADA 1 — GERADOR                        virus_hunter.py   │
│ Lê flags, descobre amostras, consulta CPU/RAM dos nós,      │
│ e ESCREVE ~40 scripts .sh + pipeline_run.sh                 │
└─────────────────────────────────────────────────────────────┘
                            ↓ gera
┌─────────────────────────────────────────────────────────────┐
│ CAMADA 2 — EXECUÇÃO             pipeline_run.sh, schedule2  │
│ `source *.sh` com `cmd &` + `wait`, ou schedule2.py para    │
│ distribuir jobs por SSH entre os nós                        │
└─────────────────────────────────────────────────────────────┘
                            ↓ invoca
┌─────────────────────────────────────────────────────────────┐
│ CAMADA 3 — WORKERS                         ~49 scripts .py  │
│ Uma responsabilidade cada, invocados por caminho absoluto,  │
│ comunicando-se exclusivamente por arquivos                  │
└─────────────────────────────────────────────────────────────┘
```

### Camada 2 em detalhe

Há **dois** mecanismos de paralelismo coexistindo:

| Mecanismo | Uso | Detecção de falha |
|---|---|---|
| `ssh <nó> <cmd> &` + `wait` a cada `nservers` jobs | maioria das etapas | nenhuma |
| [`schedule2.py`](../script/schedule2.py) | BLAST e bowtie | **existência do arquivo de saída** |

`schedule2.py` considera um job concluído se o arquivo de saída existe e tem tamanho
maior que zero ([linhas 14-25](../script/schedule2.py#L14-L25)) — **não** pelo código de
saída. Um BLAST que morreu por falta de memória depois de escrever XML parcial conta como
sucesso. Em seguida, `blast_parser.py` engole o XML truncado
([linha 88](../script/blast_parser.py#L88): `except: print 'bad xml'`) e o pipeline
prossegue com dados incompletos.

`run_all()` é chamado **duas vezes** ([linhas 123-124](../script/schedule2.py#L123-L124))
"para compensar falhas" — o que também significa que jobs podem ser reexecutados em nós
diferentes entre uma passada e outra.

---

## O que é alcançável

Medindo a partir de `virus_hunter.py`: **48 scripts invocados diretamente**, mais
`viralCount.py` (chamado por `blast_output_sort.py`) e `get_CPU.py` (chamado via SSH).

**Cerca de 50 de 155 arquivos `.py` pertencem ao pipeline viral. Os outros ~68% não.**

| Categoria | Exemplos |
|---|---|
| RNA-seq | `RNASeq.py`, `salmonRNASeq.py`, `STAR.py`, `miRNASeq.py` |
| ChIP-seq | `macs.py`, `peak.py`, `superEnhancer.R`, `wig*.py`, `ChromSizes/` |
| Variantes | `gatk.py`, `VCF*.py`, `pileup*.py`, `HIV_variants.py` |
| Depreciados | `blast_output_sort_depreciate.py`, `schedule_depre.py` |
| Duplicatas por sufixo | `nr_virus{,2,3}.py`, `fa2fq{,2}.py`, `blast_parser{,_simple,_sub,_tab}.py` |
| Artefatos de build | `virus_hunter.pyc`, `wait.gif` |

O repositório é a caixa de ferramentas de um laboratório inteiro depositada em um único
diretório, não um pipeline. Isso é o principal obstáculo para alguém novo entender o
projeto: não há como distinguir o que importa do que não importa sem análise de
alcançabilidade.

---

## Acoplamentos que dificultam a mudança

### Configuração como estado global mutável

Os parâmetros vivem como variáveis de módulo
([`virus_hunter.py:177-306`](../script/virus_hunter.py#L177-L306)) e como literais dentro
do `__main__` ([1950-1992](../script/virus_hunter.py#L1950-L1992)). Funções declaram
`global seeds, pair` e os reatribuem: [`mergePairFq()`](../script/virus_hunter.py#L562-L586)
substitui `seeds` e muda `pair` para o resto do processo.

Não existe caminho para configurar uma execução sem editar o código.

### Efeito colateral em tempo de importação

[`virus_hunter.py:205`](../script/virus_hunter.py#L205):

```python
SI=serverInfo()
```

Está no **nível do módulo**. Importar `virus_hunter` — para testar, inspecionar ou
reaproveitar qualquer função — dispara `os.system('rm server.info')` e SSH para 20
servidores. Se o cluster não responder, o import falha.

**Isso torna o arquivo inteiro não importável, não testável e não analisável
estaticamente.** É provavelmente o motivo pelo qual o trabalho anterior do grupo (jan/2025)
foi feito em `readseeds2.py`, que não tem essa chamada.

### Caminhos absolutos espalhados

817 ocorrências de `/mnt/` em 41 arquivos. Não apenas no orquestrador — os **workers**
também têm caminhos embutidos, e eles **divergem entre si**:

| Arquivo | Caminho do FASTA viral |
|---|---|
| [`blast_filter_NR.py:28`](../script/blast_filter_NR.py#L28) | `/mnt/cluster/xdeng/blastdb/virus/virus.fa` |
| [`diamond_filter_NR.py:28`](../script/diamond_filter_NR.py#L28) | `/mnt/cluster/xdeng/blastdb/virus.fa` |

Não determinado se apontavam para o mesmo arquivo via symlink. Se não, os dois filtros
usavam conjuntos de referência diferentes. Resolver exigiria a listagem do sistema de
arquivos do cluster original.

### Ausência de abstrações

Não existe conceito de *etapa*, *amostra* ou *arquivo de dados*. Cada uma das ~40 funções
geradoras reimplementa o mesmo bloco:

```python
for (key, fqfiles) in seeds.items():
    serverTag = 'ssh '+servers[job%nservers]
    f.write(serverTag + ' ' + dirscr + '<script>.py ' + <caminhos concatenados> + ' &\n')
    job+=1
    if job%nservers==0: f.write('wait\n')
```

A única classe do projeto é `Node` (árvore taxonômica), e ela está **copiada** entre
[`acc_tax.py:16`](../script/acc_tax.py#L16) e [`nr_virus3.py:42`](../script/nr_virus3.py#L42)
com comportamento **divergente**: o filtro de níveis em `printTree` está ativo em um e
comentado no outro.

A função `CacheLines()` está copiada literalmente em pelo menos cinco arquivos.

### Nomenclatura

| Nome | Problema |
|---|---|
| `trinity()`, `trinity.sh`, `trinity_<amostra>/` | Executa **SPAdes** |
| `_contig`, `_contig2`, `_contig3`, `_contig4`, `_c` | Números não indicam semântica |
| `f`, `f1`, `f2`, … `f65`, `f400`, `fff` | 22 handles em [`blastVirus()`](../script/virus_hunter.py#L1696-L1933) |
| `doMyth` | "Myth" = "mystery" (contigs sem hit) |
| `cahche` | [`samNT.py:40`](../script/samNT.py#L40) — parâmetro com typo, ignorado |
| `*_depreciate.py` | Grafia incorreta de "deprecated" |

---

## Qual parece ter sido a arquitetura pretendida

**Inferência, não afirmação do código.** A evidência aponta para uma intenção coerente:

> Um gerador que compila uma configuração de alto nível em um plano de execução paralelo,
> rodado sobre um cluster HPC compartilhado, com etapas independentes acopladas por
> arquivos.

Isso é essencialmente **o que Snakemake e Nextflow fazem** — escrito à mão antes dessas
ferramentas serem padrão em bioinformática. Os flags booleanos são uma linguagem de
configuração rudimentar; `pipeline_run.sh` é o DAG compilado; os workers são as regras.

A evidência mais forte dessa leitura está dentro do próprio repositório:
[`script/ensembleAssembly_1/`](../script/ensembleAssembly_1/) é um subprojeto do mesmo
autor, empacotado **corretamente** — com `config.txt` declarativo, `readme.txt` de
usuário, separação `bin/`, dados de exemplo e projeto de exemplo:

```
PE=260 30 FULL_PATH/test1.fastq FULL_PATH/test2.fastq
NUM_THREADS= 8
SOAP_KMER=31
ABYSS_KMER = 31
CON_LEN_DBG=150
CON_LEN_OLC=300
ASSEMBLY_MODE=optimal
```

O mesmo autor, aplicando um padrão muito melhor num escopo menor. O padrão-alvo da
refatoração já existe no repositório — só nunca foi aplicado ao pipeline principal.

---

## O que impede testar

1. Nenhum módulo é importável (efeito colateral no import).
2. Nenhuma função é pura: todas escrevem arquivos e leem globais.
3. Não há injeção de dependência: caminhos, servidores e bancos são constantes de módulo.
4. A saída é shell, cuja correção só é observável executando em cluster com bancos de
   vários terabytes.
5. Não existe nenhum teste, dado de exemplo ou saída de referência no repositório.

**Consequência prática: hoje não há como demonstrar que uma mudança preservou o
comportamento.** Enquanto isso for verdade, qualquer alteração em código de pipeline é
uma aposta. Ver a proposta de validação em [`known-issues.md`](known-issues.md).
