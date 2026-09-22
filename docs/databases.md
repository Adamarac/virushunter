# Bancos de dados

O pipeline não roda sem eles, e eles não vêm com o projeto. Esta é a maior barreira
pendente.

**E não basta baixar.** O pipeline não usa os bancos da NCBI como vêm: ele depende de
cabeçalhos com a taxonomia embutida, produzidos por
[`script/database/split_by_taxonomy.py`](../script/database/split_by_taxonomy.py).

## Por que o cabeçalho importa

Cada sequência do banco precisa terminar assim:

```
>V1.1 species$Lettuce_necrotic_stunt_virus:genus$Tombusvirus:family$Tombusviridae:category$ssRNA_viruses
```

- [`report/build_report.py`](../script/report/build_report.py) tira **espécie, gênero e
  família** desse texto. Com um FASTA comum do RefSeq, a leitura cai no `except` e **todo
  hit vira `NA`, sem erro nenhum** — o relatório sai vazio de taxonomia e o gráfico de
  pizza fica com uma fatia só.
- [`search/filter_nr.py`](../script/search/filter_nr.py) decide o descarte pelo prefixo:
  no banco do DIAMOND cada entrada nasce como `VIRUS_`, `PHAGE_` ou `NV_`, e um candidato
  cujo melhor acerto não seja `VIRUS_` é descartado.

Isso também significa que **não dá para trocar esse banco por um NR pronto** nem por
filtragem de táxon do DIAMOND: sem os rótulos, todo acerto cairia na lista negra.

## Quanto pesa

Medido em setembro de 2026, direto da NCBI.

### Para baixar

| Arquivo | Tamanho | Para quê |
|---|---|---|
| `nr.gz` | 186 GB | a fonte de tudo — 1,14 bilhão de proteínas, 430 bilhões de aminoácidos |
| `prot.accession2taxid.gz` | 11 GB | liga cada proteína à sua espécie, quando o nome do organismo não resolve |
| `nucl_gb.accession2taxid.gz` | 2,5 GB | o mesmo, para nucleotídeos |
| `taxdump.tar.gz` | 74 MB | a árvore taxonômica (`nodes.dmp`, `names.dmp`) |
| `viral.1.protein.faa.gz` | 100 MB | proteínas virais do RefSeq |
| `viral.1.1.genomic.fna.gz` | 166 MB | genomas virais, só para a rota `nucleotide` |
| índice bowtie2 do GRCh38 | 3,5 GB | filtro de hospedeiro, já pronto |
| **total** | **~204 GB** | |

### Depois de construído

| Banco | Tamanho | Rota |
|---|---|---|
| `diamond.dmnd` | **400–550 GB** *(estimativa)* | padrão — é o gigante |
| `virus_mask`, `phage_mask` | pequenos (fração viral do NR) | padrão / `phage` |
| `virus_DNA_mask` | pequeno | `nucleotide` |
| índice humano | ~4 GB | padrão |

A estimativa do DIAMOND vem dos 430 bilhões de aminoácidos mais 1,14 bilhão de rótulos.
**Não foi medida** — só construindo se sabe.

**No pico** convivem o `nr.gz`, o `diamond.fa` descompactado e o `.dmnd` sendo gerado:
**na ordem de 1 TB**. Depois dá para apagar os dois primeiros.

### Rotas que não valem o custo

- **`nr-filter-blast`** precisa do banco `nvnr`, que **só a versão antiga (`nr_virus2.py`)
  gerava** — a atual não escreve essa saída.
- **`nt`** exigiria índices bowtie2 sobre um banco de 1,08 TB, e as contagens dela não são
  confiáveis ([K2](known-issues.md)). Não recomendada.
- **`clark`** e **`remove-bacteria`**: não medidas.

## O procedimento

Tudo abaixo roda no diretório onde os bancos vão morar, com o ambiente ativo
(`conda activate virushunter`). Use `tmux`: são horas de download.

### 1. Baixar

```sh
mkdir -p ~/db && cd ~/db
wget -c https://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz
wget -c https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid/prot.accession2taxid.gz
wget -c https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid/nucl_gb.accession2taxid.gz
wget -c https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz
tar xzf taxdump.tar.gz nodes.dmp names.dmp
wget -c https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/viral.1.protein.faa.gz
wget -c https://ftp.ncbi.nlm.nih.gov/refseq/release/viral/viral.1.1.genomic.fna.gz
zcat viral.1.protein.faa.gz  | gzip > viral.protein.fa.gz
zcat viral.1.1.genomic.fna.gz | gzip > viral.genomic.fa.gz
wget -c https://genome-idx.s3.amazonaws.com/bt/GRCh38_noalt_as.zip && unzip GRCh38_noalt_as.zip
```

O `-c` retoma de onde parou — importante com 186 GB.

### 2. Separar por taxonomia

```sh
python <projeto>/script/database/split_by_taxonomy.py proteins
```

Produz `virus.fa`, `phage.fa`, `human.virome.fa` e `diamond.fa`, todos com a taxonomia no
cabeçalho — e também o `HERVaa.fasta`, se ele ainda não existir na pasta (ver abaixo).
Para a rota `nucleotide`, depois:

```sh
python <projeto>/script/database/split_by_taxonomy.py dna     # -> virus.DNA.fa
```

### 3. Formatar os bancos

```sh
segmasker -locut 0.9 -hicut 2.5 -in virus.fa -infmt fasta -parse_seqids \
          -outfmt maskinfo_asn1_bin -out virus_mask.asnb
makeblastdb -in virus.fa -dbtype prot -parse_seqids -mask_data virus_mask.asnb -out virus_mask

segmasker -locut 0.9 -hicut 2.5 -in phage.fa -infmt fasta -parse_seqids \
          -outfmt maskinfo_asn1_bin -out phage_mask.asnb
makeblastdb -in phage.fa -dbtype prot -parse_seqids -mask_data phage_mask.asnb -out phage_mask

diamond makedb --in diamond.fa -d diamond

# so para a rota nucleotide
dustmasker -in virus.DNA.fa -infmt fasta -parse_seqids \
           -outfmt maskinfo_asn1_bin -out virus_DNA_mask.asnb
makeblastdb -in virus.DNA.fa -dbtype nucl -parse_seqids -out virus_DNA_mask
```

Estes comandos estavam dentro do script antigo, via `os.system`, a maioria comentada.
Saíram para cá: são chamadas de ferramenta, e o projeto trata ferramentas pela
configuração ([ADR-0022](decisions/0022-migrate-taxonomy-split.md)).

### 4. Apontar a configuração

`config/default.yaml` traz caminhos relativos (`db/...`), e eles **não** são resolvidos
contra a raiz do projeto — valem em relação ao diretório de trabalho da amostra. Para uma
execução real, use caminhos absolutos:

```yaml
databases:
  virus_protein: "/home/<usuario>/db/virus_mask"
  diamond_nr: "/home/<usuario>/db/diamond.dmnd"
  human_bowtie_index: "/home/<usuario>/db/GRCh38_noalt_as/GRCh38_noalt_as"
```

## Três pontos de atenção

**1. O `HERVaa.fasta` é montado sozinho.** O passo 2 junta ao banco viral um arquivo de
retrovírus endógenos humanos, para que eles não sejam reportados como achados. Esse arquivo
**nunca esteve no repositório**, em nenhum commit, e não há registro de sua origem — o nome
da função que o usa (`addLinlinHerv`) sugere que veio de uma pessoa do grupo.

Não precisa mais de download nenhum: **o script já identifica os HERV dentro do NR** — é
assim que ele os separa — e antes só os descartava. Agora ele escreve esses mesmos
registros num `HERVaa.fasta`, na mesma passagem. O comando padrão basta:

```sh
python <projeto>/script/database/split_by_taxonomy.py proteins
```

A regra é simples e o script diz na tela qual caminho tomou:

| Situação | O que acontece |
|---|---|
| já existe um `HERVaa.fasta` na pasta | **usa o que está lá**, não sobrescreve |
| não existe | monta a partir dos HERV do NR |
| `--refazer-herv` | refaz mesmo existindo |

Um arquivo curado pelo grupo, portanto, tem precedência — é só deixá-lo na pasta antes de
rodar. E quando ele está presente, a saída é **byte a byte igual à do script original**,
verificado ([ADR-0023](decisions/0023-herv-by-default.md)).

O conjunto gerado é autossuficiente e reproduzível: passa a ser exatamente o que o pipeline
considera HERV, pelo mesmo critério de taxonomia (o nome científico
`Human endogenous retroviruses`, táxon 206037). Se preferir uma origem externa:

| Origem | Quantas sequências | Observação |
|---|---|---|
| NCBI, `txid206037` | 550 proteínas | inclui descendentes do táxon |
| UniProt, `taxonomy_id:206037` | 71 proteínas | conjunto menor, nenhuma revisada |

**Qual conjunto usar continua sendo decisão científica, não técnica.** O arquivo original
pode ter sido curado à mão e conter sequências que o NR não traz, ou excluir algumas que
ele traz.

**2. A memória.** O mapa de accessions tem mais de um bilhão de entradas; guardá-lo inteiro
custaria centenas de GB de RAM. O script agora faz duas passagens — descobre quais
accessions o arquivo de entrada cita e lê só esses. Provado equivalente: as duas
modalidades produzem saída idêntica. A modalidade original segue disponível em
`--mapa-inteiro`, para quem tiver a memória.

**3. O índice humano não é o mesmo.** O original usava um `mrnadna_bowtie` próprio (mRNA e
DNA humanos). O GRCh38 é o substituto moderno, não o mesmo arquivo — os resultados do
filtro de hospedeiro vão diferir.

## Periodicidade

O registro original mandava refazer em janeiro, abril, julho e outubro, e reinstalar o
BLAST em janeiro e julho. A última atualização anotada é de 2012.

Sem versionar o banco junto do resultado, nenhuma análise é reproduzível depois de uma
atualização — ver [K6](known-issues.md).

## Credenciais

O `script/readme.txt` original tinha uma senha em texto claro para um FTP externo, além das
que estavam no orquestrador. Remover os arquivos **não desfaz a exposição** —
ver [K4](known-issues.md).
