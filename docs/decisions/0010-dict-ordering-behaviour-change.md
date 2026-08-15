# 0010 — Mudança forçada de comportamento: ordem de iteração de dicionário

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

A Fase 1 da migração converteu `virus_hunter.py` para Python 3 (`2to3` com o conjunto
padrão de *fixers*: `print`, `xrange`, `has_key`, `except`, `raise`). Nenhuma lógica foi
tocada. Ainda assim, a saída do gerador **divergiu** da referência congelada em Python 2.

A causa não é a conversão: é a linguagem. Em Python 2 a ordem de iteração de `dict` é
arbitrária, derivada do hash; em Python 3.7+ é a ordem de inserção. O gerador itera
`seeds.items()` para distribuir amostras entre os nós e para montar comandos de agregação,
então a ordem muda.

Isso é o [K7](../known-issues.md) — "ordem de iteração de dicionário afeta atribuição de
nós, índices de fatia e ordem de concatenação" — se materializando.

**Não é evitável.** Nenhuma escrita de código Python 3 reproduz a ordem de hash do Python 2.

### O que exatamente mudou

Comparação insensível a nó e a ordem de linha
(`compare_normalized.sh`), entre a captura
Python 2 (commit `2705fa7`) e a Python 3:

| Resultado | Artefatos |
|---|---|
| Conjunto de trabalho **idêntico** | **39** |
| Divergentes | 5 |

Os 39 idênticos diferem apenas em **qual nó** recebe cada amostra e na ordem das linhas —
o mesmo conjunto de comandos, com os mesmos parâmetros, sobre as mesmas amostras.

Os 5 divergentes são todos comandos de **agregação**, cuja ordem de argumentos segue a
iteração das amostras:

| Artefato | Diferença |
|---|---|
| `blast_output_merge.sh` | `cat S2 S1 > all` → `cat S1 S2 > all` |
| `bowtieHTML.sh` | ordem dos argumentos de `summaryCount.py` |
| `mergeTable.sh` | ordem dos argumentos de `mergeTable.py` |
| `vfam_annot.sh` | ordem dos operandos do `cat` |
| `sra.sh` | **barcode atribuído a cada amostra troca** (`AAAAAG` ↔ `AAAAAC`) |

Os quatro primeiros mudam a **ordem das linhas** dentro do arquivo agregado, não o
conteúdo. O parsing a jusante ([`blast_output_sort.py`](../../script/blast_output_sort.py))
agrupa por vírus e lê blocos de 11 linhas (invariante
[I4](../invariants.md)), que permanecem íntegros.

`sra.sh` é diferente em espécie: a associação amostra↔barcode muda, o que importaria numa
submissão ao SRA. A rota está desligada na configuração de referência (`sra=False`), então
não entra no `pipeline_run.sh`.

### Um efeito colateral positivo

Em Python 3 a saída passou a ser **determinística e significativa**: a ordem de iteração
é a ordem do `fastq/samples.txt`. Verificado com duas capturas consecutivas — idênticas.

Em Python 2 não era: a ordem dependia do hash. Ou seja, a migração **remove** uma das
fontes de não-determinismo listadas em K7.

### Uma corrida descoberta no processo

Duas capturas Python 3 ainda divergiam numa linha: o `print` do dicionário `SI`.
`serverInfo()` dispara um `ssh` por nó, todos concorrendo com `>> server.info`, então a
ordem de chegada das linhas é uma corrida. `SI` só é lido por chave, então isso afeta
apenas o diagnóstico impresso. É comportamento **anterior** à migração; a captura filtra
essa linha.

## Alternativas consideradas

**Ordenar `seeds` explicitamente.** Tornaria a ordem definida por contrato em vez de
incidental. Descartada agora: mudaria o comportamento numa terceira direção, distinta tanto
do Python 2 quanto do Python 3, sem necessidade — a ordem do `samples.txt` já é
determinística e defensável. Fica registrada como melhoria futura, junto ao resto de K7.

**Manter a referência Python 2 e comparar sempre normalizado.** Descartada: enfraquece a
verificação permanentemente, trocando comparação byte a byte por uma que ignora ordem e
esconderia regressões reais de escalonamento.

**Re-congelar a referência a partir do Python 3.** Recupera a comparação byte a byte para
todo o trabalho seguinte, ao custo de aceitar formalmente a mudança desta ADR.

## Decisão

1. **Aceitar a mudança de ordenação** como consequência inevitável da migração.
2. **Re-congelar** `tests/reference/expected/` a partir da saída Python 3. A referência
   Python 2 permanece no histórico, em `git show 2705fa7:tests/reference/expected/<arquivo>`.
3. **Preservar a evidência como ferramenta**, não como afirmação:
   `compare_normalized.sh` reproduz a
   comparação a qualquer momento.
4. **Não** ordenar `seeds` neste incremento — seria uma terceira mudança de comportamento.

## Consequências

- A comparação byte a byte volta a valer para as fases seguintes da migração, que é o que
  as protege.
- A atribuição amostra↔nó mudou. Cientificamente irrelevante num cluster homogêneo; num
  heterogêneo interage com K7 (o teto de memória do SPAdes vem do nó), que segue aberto.
- A ordem das linhas nos arquivos agregados mudou. O conteúdo, não.
- **`sra.sh` atribui barcodes diferentes.** Se a rota SRA vier a ser usada, conferir os
  barcodes antes de submeter. Registrado aqui porque é a única diferença de espécie, não só
  de ordem.
- Uma fonte de não-determinismo do K7 desapareceu; as outras (reexecução do `schedule2.py`,
  memória do SPAdes vinda do nó, mutação de banco) continuam.
