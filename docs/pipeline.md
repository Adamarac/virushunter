# Fluxo real de execução

Reconstruído a partir do código, não da estrutura de diretórios. A referência principal é
o bloco `__main__` de [`script/virus_hunter.py:1937-2233`](../script/virus_hunter.py#L1937-L2233),
que define simultaneamente os parâmetros **e** a ordem em que `pipeline_run.sh` é escrito.

> **Escopo.** Este documento descreve o fluxo de `virus_hunter.py`, o orquestrador mais
> abrangente. Onde `readseeds2.py` difere de forma relevante, há uma nota. A escolha de
> qual dos dois é a referência ainda está **pendente** — ver
> [ADR-0003](decisions/0003-canonical-orchestrator.md) e [`orchestrators.md`](orchestrators.md).

---

## O ponto que muda tudo: o orquestrador não executa nada

`virus_hunter.py` **gera** o pipeline; não o roda. Ao ser executado, escreve cerca de 40
arquivos `.sh` no diretório de trabalho, mais um `pipeline_run.sh` que os encadeia. A
execução real acontece depois, quando o usuário roda `sh pipeline_run.sh`.

```
python virus_hunter.py     →  gera  *.sh  +  pipeline_run.sh
sh pipeline_run.sh         →  executa o pipeline
```

Consequências práticas:

- Mudar um parâmetro exige **editar o código-fonte** e regerar os scripts.
- Os `.sh` gerados são o artefato executável real, e **não são versionados**.
- Os scripts gerados incorporam caminhos absolutos e nomes de servidores do momento da
  geração; não são portáveis nem reexecutáveis em outro ambiente.

## Parâmetros no estado commitado

De [`virus_hunter.py:1950-1992`](../script/virus_hunter.py#L1950-L1992):

| Parâmetro | Valor | Efeito |
|---|---|---|
| `pair` | `False` | Modo single-end |
| `keep_human` / `keep_bac` | `False` / `True` | Remove humano, **mantém** bactérias |
| `dedup` | `True` | Deduplicação ativa |
| `rm_adaptor` | `False` | **Sem remoção de adaptador nem trim de qualidade** |
| `doAssembly` | `'no'` | **Sem montagem** |
| `donrfilter` | `True` | Filtro NR ativo (via DIAMOND) |
| `doClark`, `doNT`, `doMyth`, `doHmmer`, `doreAssemb` | `False` | Rotas opcionais desligadas |
| `n` | `50` | Número de fatias da query |
| `EVALUE` | `'0.01'` | Limiar de e-value |
| `length` | `50` | Comprimento mínimo de leitura para BLAST |
| `contigLength1` / `contigLength2` | `300` / `1500` | Cortes de contig antes/depois do CAP3 |
| `myslen` | `1000` | Comprimento mínimo de contig "mystery" |
| `thread` | `'48'` | Threads por job |

**No estado commitado, o pipeline é busca viral no nível de leitura, sem montagem e sem
trim de adaptador.** Não determinado se esse é o estado de produção ou um estado de teste
deixado no último commit — resolver exigiria logs de execução ou um `run.log` real.

---

## Visão geral

```
FASTQ bruto
  ↓  E1  descoberta de amostras
  ↓  E2  conversões opcionais de entrada
  ↓  E3  depleção de hospedeiro e bactérias      bowtie2
  ↓  E4  deduplicação clonal                     dedup.py
  ↓  E5  adaptador e qualidade                   blastn + trim_quality.py
  ↓  E6  limpeza de pares e QC                   fq_pair_clean.py, polyA.py, R
  ↓  E7  preparo de leituras
  ↓  E8  classificação taxonômica  [opcional]    CLARK / bowtie2 vs nt
  ↓  E9  montagem                  [opcional]    SOAP+ABySS+MetaVelvet→CAP3 | SPAdes
  ↓  E10 combinação e fatiamento
  ↓  E11 triagem viral                           blastx | DIAMOND | blastn
  ↓  E12 parsing e separação de "mystery"        blast_parser.py
  ↓  E13 filtro contra NR                        DIAMOND + diamond_filter_NR.py
  ↓  E14 agregação e relatório                   blast_output_sort.py
  ↓  E15 publicação web                          firstpage.py + PHP
       E16 anotação HMM      [opcional]          HMMER + vFam
       E17 remontagem cruzada [opcional]         CAP3 + bowtie2 + tally
```

---

## E1 — Descoberta de amostras

- **Entrada:** `fastq/samples.txt`, gerado **manualmente** (`ls -1 *.gz > samples.txt`)
- **Processo:** [`readSeeds2()`](../script/virus_hunter.py#L519-L560) agrupa arquivos em amostras
- **Saída:** dicionário `seeds` em memória, `run.log`, `server.txt`
- **Alimenta:** todas as etapas — é a raiz do fan-out

A chave da amostra vem de `line.strip().split('.')[0].split('_')[1]`
([linha 534](../script/virus_hunter.py#L534)) — **posicional e frágil**: depende da
convenção de nomes do sequenciador. Um arquivo `A_S1_L001_R1_001.fastq.gz` vira a chave
`S1`. Nomes fora dessa convenção agrupam errado, sem aviso.

Máximo de dois arquivos por chave; o terceiro cria uma chave `<key>.2`.

## E2 — Conversões opcionais de entrada

FASTA→FASTQ (`fa2fq2.py`), BAM→FASTQ (Picard `SamToFastq`), unzip, preparo SRA
(`sra.py`), fusão de pares sobrepostos (**FLASH** `-M 250`,
[linha 569](../script/virus_hunter.py#L569)). Todas desligadas no estado commitado.

## E3 — Depleção de hospedeiro e bactérias

- **Entrada:** FASTQ bruto
- **Ferramenta:** **bowtie2** `--quiet --local --very-fast-local --no-hd --reorder -p 7`
- **Referências:** hg38 genoma+mRNA; 27 índices bacterianos derivados do `nt` particionado
- **Saída:** `<amostra>_<i>.fil` — mesma contagem de registros, leituras de hospedeiro
  reduzidas a `A` (ver [I1](invariants.md#i1--a-identidade-de-uma-leitura-é-a-sua-posição-no-arquivo))
- **Alimenta:** E4

[`bowtieBac()`](../script/virus_hunter.py#L950-L976) escreve `bowtieBac.txt` — uma lista
de jobs, não um `.sh` — consumida por `schedule2.py`. Em seguida
[`sam2fq_bac.py`](../script/sam2fq_bac.py) lê os SAMs em lockstep posicional
(ver [I2](invariants.md#i2--arquivos-paralelos-são-lidos-em-correspondência-posicional))
e mascara leituras alinhadas com pelo menos 20 bp.

`--very-fast-local` privilegia velocidade sobre sensibilidade. É defensável aqui: o
objetivo é **descartar** hospedeiro, e um falso negativo custa apenas processamento extra
adiante. (Interpretação, não afirmação do código.)

**Atalho:** se `keep_human and keep_bac`, roda `skipbowtie.sh`, que apenas faz
`zcat`/`cat` — nenhuma filtragem ocorre.

## E4 — Deduplicação clonal

- **Ferramenta:** [`dedup.py`](../script/dedup.py) (in-house)
- **Processo:** particiona o FASTQ em 257 buckets por prefixo de 4 nt, marca duplicatas
  comparando os **primeiros 50 bp**, e reordena pela posição original
- **Saída:** `.dup`, mais as métricas `num_dup_reads` e `percent_dup` no stdout
- **Alimenta:** E5

## E5 — Adaptador e qualidade

Com `rm_adaptor=True`: FASTA (`fq2faID.py`) → `makeblastdb` por amostra → **blastn dos
adaptadores contra as leituras** (query = [`adaptor.fa`](../script/adaptor.fa), db = leituras,
`-evalue 1 -max_target_seqs 100000000`) → [`blast_trim.py`](../script/blast_trim.py) →
[`trim_quality.py`](../script/trim_quality.py).

Detectar adaptador por BLAST em vez de usar cutadapt/Trimmomatic é uma escolha incomum.
Permite adaptadores arbitrários sem reconfigurar ferramenta, ao custo de construir um
banco BLAST por amostra. (Interpretação.)

**Com `rm_adaptor=False` — o estado commitado — apenas `recodeID.py` roda: nenhuma
remoção de adaptador e nenhum trim de qualidade acontecem.**

`trim_quality.py` contém a regra fixa `if zz<40: pass`
([linha 127](../script/trim_quality.py#L127)): os primeiros 40 bp nunca são avaliados por
qualidade. Constante mágica, não configurável, sem justificativa registrada.

## E6 — Limpeza de pares e QC

[`fq_pair_clean.py`](../script/fq_pair_clean.py) descarta pares em que ambas as leituras
têm 5 bp ou menos — é aqui que as leituras mascaradas em E3/E4 efetivamente saem.
[`polyA.py`](../script/polyA.py) gera scripts R (`R CMD BATCH`) com histogramas
antes/depois.

## E7 — Preparo de leituras

`cat` de R1+R2 → `.fq`; `fq2fa.py` com corte de 50 bp → `.fa`; `fqLenFilter.py` com corte
de 35 bp → `abyss.fq`.

## E8 — Classificação taxonômica (opcional, desligada)

- **CLARK** (k=20, n=48) contra três bancos → `clark_result.py` → `clark_html.py`
- **bowtie2 contra 14 índices `nt`** → [`samNT.py`](../script/samNT.py) → contagens por
  categoria/classe/família/espécie

> ⚠️ A rota NT contém um defeito que invalida as contagens — ver
> [`known-issues.md`](known-issues.md).

## E9 — Montagem (opcional; `'no'` no estado commitado)

| Modo | Ferramentas | Saída |
|---|---|---|
| `'denovo'` | SOAPdenovo2 (k=31), ABySS (k=31), MetaVelvet (k=31), ABySS particionado → **CAP3** (`-o 25 -p 80`) | `contig_SAVaC/` |
| `'trinity'` | **SPAdes** `--meta -k 21,33,55,77 -t 48` | `trinity_<amostra>/` |
| `'no'` | — | nenhuma |

Filtros de comprimento: 300 bp antes do CAP3, 1500 bp depois.

> **Nomenclatura enganosa.** A função `trinity()` executa **SPAdes**, não Trinity — o
> próprio código admite: `def trinity(RAM): #This is actually spade`
> ([linha 1667](../script/virus_hunter.py#L1667)). Todos os artefatos herdam o nome errado.

MIRA e Minimo existem no código mas não são alcançáveis pelas ramificações atuais.

> **`readseeds2.py` difere aqui:** sempre monta (SOAP + MetaVelvet + ABySS + ABySS
> particionado + MIRA → CAP3), sem flag para desligar.

## E10 — Combinação e fatiamento

`cat <amostra>_contig4 <amostra>.fa > <amostra>_c` — **contigs e leituras cruas viram a
mesma query**. `splitQuery.py` divide em `n=50` fatias.

Com `doAssembly='no'`, `_contig4` nunca é criado; o `cat` falha nesse operando e prossegue
com o `.fa`. O pipeline continua funcionando por tolerância do `cat`, não por desenho.

## E11 — Triagem viral

- **Padrão:** `blastx` contra `virus_mask` (banco de **proteína** viral com soft-masking)
- **Parâmetros:** `-evalue 0.01 -outfmt 5 -dbsize 10000000 -searchsp 1000000000
  -max_target_seqs 1 -db_soft_mask 21 -best_hit_overhang 0.1 -best_hit_score_edge 0.1`
- **Alternativas:** DIAMOND blastx (`--sensitive`, exige `fixDiamondXML.py`) ou blastn
  contra `virus_DNA_mask`
- **Execução:** `blast_virus.txt` → `schedule2.py`
- **Saída:** XML BLAST por fatia

Busca em espaço de proteína é o núcleo científico: detecta vírus divergentes que uma busca
de nucleotídeo perderia.

## E12 — Parsing e separação de "mystery"

[`blast_parser.py`](../script/blast_parser.py) usa **Biopython `NCBIXML`** e separa:

- queries com `hsp.expect < 0.01` → FASTA `_s` (candidatos virais) → alimenta E13
- queries **sem** hit e com mais de `myslen=1000` bp → conjunto **"mystery"** —
  candidatos a vírus novos ou muito divergentes → alimenta E16

## E13 — Filtro contra NR

DIAMOND blastx contra o banco não-viral → `.m8` →
[`diamond_filter_NR.py`](../script/diamond_filter_NR.py) monta uma lista negra das queries
cujo melhor hit não é viral e as remove.

A variante legada [`blast_filter_NR.py`](../script/blast_filter_NR.py) faz uma comparação
de e-values (um hit viral só passa se seu e-value for melhor que o do melhor hit
não-viral) — cientificamente mais forte, porém **desativada**
([linha 2208](../script/virus_hunter.py#L2208) está comentada).

> **`readseeds2.py` difere aqui:** usa a rota BLAST + `blast_filter_NR.py`, não DIAMOND.

**Saída:** `<amostra>_blast_filter.txt`, em blocos posicionais de 11 linhas
(ver [I4](invariants.md#i4--um-resultado-é-um-bloco-posicional-de-exatamente-11-linhas)).

## E14 — Agregação e relatório

[`blast_output_sort.py`](../script/blast_output_sort.py) agrupa por espécie viral, calcula
menor e-value viral e não-viral, conta hits em três limiares (1e-2, 1e-5, 1e-10), recupera
a leitura-par e emite `aln/*.html`, `fasta/*.fa`, `pie/`, `table/` e `.xls`.

`dustmasker` + `faSort.py` tratam os contigs "mystery". `mergeTable.py` produz o
`hitTable`; `plot_pie.py` os gráficos; `firstpage.py` o índice com ~22 métricas por amostra.

## E15 — Publicação

`movetowww.sh` copia HTML/XLS/FASTA/pie e os `.php` para `<wd>/<base>/`.
`prepBlastFile.sh` cria um banco BLAST por amostra para consulta interativa via
[`blast.php`](../script/blast.php). Vários `sudo chmod 777 -R` ao longo do caminho.

## E16 — Anotação por HMM (opcional)

Contigs "mystery" → blastx NR → `dna2prot.py` → **HMMER `hmmsearch`** contra **vFam-A 2014**
→ `hmmer_annot.py`. Perfis HMM detectam homologia remota além do alcance do BLAST — a rota
para vírus verdadeiramente novos.

## E17 — Remontagem cruzada (opcional)

Junta contigs de todas as amostras → CAP3 → bowtie2 de volta → `sam2count.py` →
`tally.py` → `annotate_contig.py`. Quantificação entre amostras.

---

## Onde os dados ficam

O pipeline é um *pipes-and-filters* mediado por sistema de arquivos: cada etapa lê e
escreve arquivos, o que permite inspeção e retomada manual. O acoplamento se dá por uma
cadeia de sufixos não documentada:

```
.fil → .dup → .ada → .trim → _sequence.txt → .fa → _contig → _contig2
     → _contig3 → _contig4 → _c → _c_<i> → _s
```

Os números não indicam semântica: `_contig2` é o resultado de um filtro de comprimento,
`_contig3` é o merge de contigs e singlets do CAP3, `_contig4` é outro filtro de
comprimento. Renomear essa cadeia é uma das melhorias de maior retorno e menor risco.

> ⚠️ [`clean_dir()`](../script/virus_hunter.py#L797-L801) gera um script que apaga
> **todo arquivo que não seja `.gz`** no diretório do projeto. Não é executado por
> `pipeline_run.sh`, mas está disponível como `clean.sh`.
