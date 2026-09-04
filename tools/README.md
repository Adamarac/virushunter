# Ferramentas externas

O pipeline chama doze programas de bioinformática. Nenhum vem com o projeto.

## Caminho recomendado: ambiente conda

```sh
conda env create -f environment.yml
conda activate virushunter
```

Isso instala tudo com as versões fixadas e as bibliotecas certas, e coloca os programas no
`PATH`. `config/default.yaml` os encontra pelos nomes simples — nada mais a configurar.

| Programa | Versão | Para quê |
|---|---|---|
| blast | 2.16.0 | busca viral, bancos, máscara de baixa complexidade |
| bowtie2 | 2.5.4 | filtro de hospedeiro e rota `nt` |
| diamond | 2.1.12 | busca contra o NR e rota `diamond` |
| samtools | ≥1.19 | rota `from_bam` |
| picard | 3.5.0 | rota `from_bam` |
| sra-tools | 3.4.1 | rota `sra_prep` |
| flash | 1.2.11 | rota `merge-pairs` |
| cap3, soapdenovo2, velvet, abyss | — | rota `denovo` |
| hmmer | 3.4 | rota `hmmer` (ver [K34](../docs/known-issues.md) — a rota nunca funcionou) |

CLARK **não está no bioconda** e precisa ser obtido à parte; aponte o caminho em
`tools.clark`.

## Por que não há binários nesta pasta

Foi tentado. Extrair os binários dos pacotes conda sem o fecho completo de bibliotecas
produz programas que falham em execução por `.so` ausente — a `lib/` do BLAST sozinha tem
**420 MB**. O ambiente conda resolve isso corretamente e é menor de manter.

Se preferir um binário avulso, `config/default.yaml` aceita caminho: valores com barra são
relativos à raiz do projeto.

## Windows

Houve binários Windows aqui (BLAST+ 2.17, bowtie2 2.5.5, DIAMOND 2.2.6). Foram removidos
quando ficou decidido rodar em Linux. Continuam recuperáveis do histórico, e a
[ADR-0019](../docs/decisions/0019-local-tools.md) registra o que foi preciso para
funcionarem — inclusive duas DLLs que o BLAST exige e um atalho `python3` para o bowtie2.

Metade das ferramentas não tem build para Windows, então aquele caminho nunca cobriu a
rota de montagem.

## Bancos de dados

Continuam ausentes e são obrigatórios. Ver [docs/databases.md](../docs/databases.md).
