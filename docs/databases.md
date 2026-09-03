# Bancos de dados

O pipeline não roda sem eles, e eles não vêm com o projeto. Esta é a maior barreira
pendente: o NR completo passa de 100 GB.

O procedimento abaixo foi extraído de `script/readme.txt` e dos comentários de
`script/nr_virus.py`, ambos removidos da árvore por não fazerem parte da versão migrada
([ADR-0020](decisions/0020-prune-to-the-migrated-version.md)). O conteúdo é o registro
original, traduzido e sem os caminhos do cluster.

## O que a configuração exige

De `config/default.yaml`, seção `databases:`. A rota padrão usa apenas os três primeiros:

| Chave | O que é | Como se obtém |
|---|---|---|
| `virus_protein` | proteínas virais, com máscara | passos 1–4 abaixo |
| `diamond_nr` | banco DIAMOND do NR não viral | passo 5 |
| `human_bowtie_index` | índice bowtie2 do genoma humano | passo 6 |
| `non_viral_nr` | NR não viral para BLAST (rota `nr_filter_method: "blast"`) | passo 4 |

As demais chaves servem a rotas não migradas (fago, DNA, vFam, CLARK, NT).

## 1. Baixar

```sh
# proteínas virais do RefSeq
wget ftp://ftp.ncbi.nih.gov/refseq/release/viral/viral.1.protein.faa.gz
# NR completo (>100 GB descomprimido)
wget ftp://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz
```

## 2. Taxonomia

```sh
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxcat.zip
wget ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_prot.zip
```

**Atenção:** o `gi_taxid_prot` está descontinuado. O NCBI abandonou os números GI em favor
de accessions em 2016, e este arquivo não é mais atualizado. O procedimento original
depende dele, então **esta etapa precisa ser refeita** com
`prot.accession2taxid.gz`. *Não determinado:* o quanto de `nr_virus.py` isso invalida.

## 3. Separar viral de não viral

O original fazia isso com `python nr_virus.py`, que lê `nodes.dmp`/`names.dmp` da
taxonomia e escreve `virus.fa`, `nvrefseq.fa` e `tax_tree.txt`.

Esse script **não foi migrado** — é Python 2 e não compila em Python 3. Para recuperá-lo:

```sh
git show 505f18b:script/nr_virus.py > nr_virus.py
```

Existiam três variantes (`nr_virus.py`, `nr_virus2.py`, `nr_virus3.py`) sem registro de
qual era a corrente. *Não determinado.*

## 4. Construir os bancos BLAST

Comandos exatos, dos comentários de `nr_virus.py`:

```sh
segmasker -in virus.fa -infmt fasta -parse_seqids -outfmt maskinfo_asn1_bin -out virus_mask.asnb
makeblastdb -in virus.fa -dbtype prot -parse_seqids -mask_data virus_mask.asnb -out virus_mask
makeblastdb -in nvrefseq.fa -dbtype prot -parse_seqids -out nvrefseq
```

`virus_mask` é o valor de `databases.virus_protein`. A máscara existe para evitar que
regiões de baixa complexidade gerem semelhança espúria.

`segmasker` não está em `tools/bin/` — não entrou na extração. Está no mesmo tarball do
BLAST+ ([tools/README.md](../tools/README.md)).

## 5. Construir o banco DIAMOND

```sh
diamond makedb --in nvrefseq.fa -d diamond
```

**Um banco DIAMOND de 2015 não é legível pela versão 2.2.6 instalada aqui.** O formato
mudou entre as versões maiores. Precisa ser reconstruído.

## 6. Índice do hospedeiro

```sh
bowtie2-build genoma_humano.fa mrnadna_bowtie
```

Exige o atalho `python3` descrito em [tools/README.md](../tools/README.md).

## Periodicidade

O registro original dizia para refazer em janeiro, abril, julho e outubro, e reinstalar o
BLAST em janeiro e julho. A última atualização anotada é de 2012.

## Credenciais

`script/readme.txt` continha uma senha em texto claro para um servidor FTP externo, além
das que estão em `virus_hunter.py`. Remover o arquivo **não desfaz a exposição** — ver
[K4](known-issues.md). As credenciais estão públicas desde 2020 e precisam ser trocadas
nos sistemas de origem.
