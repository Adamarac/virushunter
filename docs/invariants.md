# Invariantes implícitos do pipeline

Quatro regras sustentam o pipeline inteiro. Nenhuma delas está documentada no código
original, nenhuma é verificada em tempo de execução, e **nenhuma produz erro quando é
violada** — produzem resultado silenciosamente errado.

Este é o documento a ler antes de modificar qualquer etapa.

---

## I1 — A identidade de uma leitura é a sua posição no arquivo

### O que o código faz

[`script/recodeID.py:12-21`](../script/recodeID.py#L12-L21) descarta o identificador
original de cada leitura e o substitui por um identificador derivado da **posição**:

```python
i=0
for line in f:
	i+=1
	if i%4==1:
		lineno=i/4
		seqid='@s'+str(lineno)+'_'+pair_end+'_'+label
```

O identificador `@s<lineno>_<par>_<biblioteca>` é a chave usada de ponta a ponta:
para reencontrar a leitura-par no relatório final
([`blast_output_sort.py:128-131`](../script/blast_output_sort.py#L128-L131)), para
agrupar hits e para recuperar sequências.

### A consequência

**Nenhuma etapa anterior à recodificação pode remover registros de um FASTQ.** Remover
uma leitura desloca todas as posteriores e reatribui as identidades — silenciosamente.

Por isso os filtros do pipeline **mascaram** em vez de remover:

| Etapa | Evidência | Comportamento |
|---|---|---|
| Deduplicação | [`dedup.py:130`](../script/dedup.py#L130) | `if read[0:50] in keyset: read='A'; qual='A'` |
| Depleção de bactérias | [`sam2fq_bac.py:92-93`](../script/sam2fq_bac.py#L92-L93) | `if bac1: seq='A'; qual='G'` |

A leitura duplicada ou de hospedeiro continua no arquivo, ocupando sua linha, reduzida a
uma única base. O filtro de comprimento posterior
([`fq_pair_clean.py:17`](../script/fq_pair_clean.py#L17)) é quem efetivamente as
descarta — **depois** que a recodificação já fixou as identidades.

`dedup.py` chega a particionar o arquivo por prefixo de 4 nucleotídeos para caber em
memória e depois **reordenar tudo de volta** pela posição original
([`dedup.py:54-87`](../script/dedup.py#L54-L87), função `RestoreOrder`) — trabalho
considerável, existente apenas para preservar este invariante.

### Como quebrar sem perceber

- Substituir `dedup.py` por uma ferramenta pronta de deduplicação. Todas removem
  leituras. As identidades passam a apontar para leituras diferentes das originais.
- Inserir qualquer filtro de qualidade que descarte registros antes da recodificação.
- Paralelizar a leitura de um FASTQ sem preservar a ordem de escrita.

### Observação sobre migração para Python 3

`lineno = i/4` usa divisão inteira do Python 2. Em Python 3, `/` passa a ser divisão
real e `lineno` vira `float` — os identificadores mudam de `@s1_1_lib` para
`@s1.0_1_lib`, quebrando todo o parsing a jusante. Deve virar `i//4`.

---

## I2 — Arquivos paralelos são lidos em correspondência posicional

### O que o código faz

Quando o pipeline alinha as mesmas leituras contra vários índices, ele confia em que a
linha *N* de cada arquivo SAM corresponde à mesma leitura. Isso é obtido passando
`--reorder` ao bowtie2 ([`virus_hunter.py:970`](../script/virus_hunter.py#L970)), que
força a saída na ordem da entrada mesmo com múltiplas threads:

```
bowtie2 --quiet --local --very-fast-local --no-hd --reorder -p 7 -x <índice> -U <fastq> -S <sam>
```

Os consumidores então leem todos os arquivos em *lockstep* — uma linha de cada, por
iteração ([`sam2fq_bac.py:52-71`](../script/sam2fq_bac.py#L52-L71)).

### A consequência

Todos os arquivos de um grupo precisam ter **exatamente o mesmo número de linhas, na
mesma ordem**. Um alinhamento que falhou pela metade não gera erro: gera
desalinhamento, e leituras diferentes passam a ser comparadas entre si.

`--no-hd` (suprimir cabeçalho SAM) não é cosmético — existe para que a contagem de
linhas seja igual à contagem de leituras.

### Violação existente no código

[`samNT.py:56-69`](../script/samNT.py#L56-L69) **quebra este invariante**:

```python
for f1 in fs1:
    line1 = f1.readline()
    ...
    if chro !='*' and len(seq)>20:
        ...
        hit=True
        break        # ← os demais handles não avançam
```

O `break` interrompe o laço no primeiro acerto, deixando os outros arquivos SAM sem
avançar. A partir da primeira leitura classificada, os handles estão dessincronizados.
Ver [`known-issues.md`](known-issues.md).

---

## I3 — A taxonomia trafega dentro do cabeçalho do banco de dados

### O que o código faz

O pipeline não consulta nenhum serviço de taxonomia em tempo de execução. A linhagem é
**embutida no cabeçalho FASTA** quando o banco é construído
([`nr_virus3.py:228-231`](../script/nr_virus3.py#L228-L231)):

```python
label.append('species'+'$'+species)
label.append('genus'+'$'+genus)
label.append('family'+'$'+family)
label.append('category'+'$'+category)
```

produzindo cabeçalhos na forma:

```
>ACC123  species$Nome_da_Especie:genus$Genero:family$Familia:category$Viruses
```

O BLAST devolve esse texto como título do *subject*, e os consumidores o desmontam:

- [`blast_output_sort.py:203-207`](../script/blast_output_sort.py#L203-L207) — `split(':')` e `split('$')`
- [`samNT.py:63`](../script/samNT.py#L63) — `cat, clas, fam, species = chro.split('$')`

### A consequência

O banco de dados **é** o canal de metadados. Reconstruir o banco com outro script, outra
versão da taxonomia NCBI ou outro separador altera os resultados taxonômicos sem que
nada no código do pipeline mude.

Os separadores `:` e `$` são reservados. `nr_virus3.py:108` os remove dos nomes
científicos justamente por isso:

```python
names[tid]=name.replace(':', '_').replace('$', '_')
```

Um nome de táxon que contivesse `$` ou `:` quebraria o parsing — a sanitização acontece
na construção do banco, e não há verificação alguma no lado do consumo.

### Atenção

`samNT.py` espera **quatro** campos separados por `$` (`cat, clas, fam, species`),
enquanto `blast_output_sort.py` espera **quatro campos separados por `:`**, cada um
com um par `chave$valor`. São formatos **diferentes**, produzidos por scripts de
construção diferentes. Confundi-los ao unificar a construção dos bancos quebraria uma
das duas rotas.

---

## I4 — Um resultado é um bloco posicional de exatamente 11 linhas

### O que o código faz

O formato de troca entre a filtragem e o relatório não tem cabeçalho, delimitador nem
esquema. É um bloco de 11 linhas em ordem fixa, escrito por
[`blast_filter_NR.py:141-158`](../script/blast_filter_NR.py#L141-L158) e por
[`diamond_filter_NR.py:103-120`](../script/diamond_filter_NR.py#L103-L120):

| # | Conteúdo |
|---|---|
| 1 | `****Alignment****` |
| 2 | identificador da query |
| 3 | `query_nt <sequência>` |
| 4 | `subject: <título com a taxonomia>` |
| 5 | `length: <n>` |
| 6 | `e value: <float>` |
| 7 | `lowest non-virus nr e value (LNVNRE) <float>` |
| 8 | `identities: <n>` |
| 9 | alinhamento — query |
| 10 | alinhamento — match |
| 11 | alinhamento — subject |

O leitor não procura marcadores. Ele conta linhas com aritmética modular sobre o arquivo
inteiro ([`blast_output_sort.py:128-166`](../script/blast_output_sort.py#L128-L166)):

```python
if i%11 == 2 and line.startswith('@'):   # identificador
if i%11 == 3:                            # query_nt
if i%11 == 4:                            # taxonomia
elif i%11 == 6:                          # e-value viral
elif i%11 == 7:                          # e-value NR
```

E recupera o bloco inteiro por deslocamento a partir da linha da taxonomia
(`cache[virus].append(i-3)`, depois `linecache.getline(input, index+i)` para
`i` em `0..10`).

### A consequência

**Acrescentar, remover ou reordenar uma única linha da saída corrompe todo o relatório —
sem erro.** Os campos passam a ser lidos das posições erradas: e-values viram
identificadores, taxonomia vira sequência. O relatório é gerado normalmente, com
conteúdo errado.

O acoplamento é entre arquivos distantes, sem nenhuma constante compartilhada: quem edita
`blast_filter_NR.py` não tem como saber que `blast_output_sort.py` depende da contagem.

Note ainda que a concatenação dos blocos por `blast_output_merge.sh` só funciona porque
todo bloco tem tamanho idêntico — qualquer bloco de tamanho diferente desalinha tudo o
que vier depois dele no arquivo concatenado.

---

## Resumo para quem for refatorar

| Invariante | Quem depende | Sintoma da violação |
|---|---|---|
| I1 — identidade = posição | recodeID, dedup, sam2fq_bac, blast_output_sort | Leituras-par erradas; identidades trocadas |
| I2 — lockstep posicional | sam2fq_bac, samNT | Leituras comparadas com as erradas |
| I3 — taxonomia no cabeçalho | nr_virus*, blast_output_sort, samNT | Táxons ausentes ou `NA` |
| I4 — bloco de 11 linhas | blast_filter_NR, diamond_filter_NR, blast_output_sort | Campos lidos das posições erradas |

Nenhuma delas gera exceção. Todas geram resultado plausível e errado.

**Recomendação** (proposta, não decidida): antes de alterar qualquer etapa, tornar cada
invariante verificável — contagem de registros entre etapas para I1 e I2, validação de
cabeçalho na construção do banco para I3, e substituição do bloco posicional por formato
com esquema explícito para I4. Ver [`known-issues.md`](known-issues.md).
