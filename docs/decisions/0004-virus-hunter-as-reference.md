# 0004 — `virus_hunter.py` é a referência científica

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M
- **Substitui:** [ADR-0003](0003-canonical-orchestrator.md)

## Contexto

[ADR-0003](0003-canonical-orchestrator.md) registrou a escolha do orquestrador como
pendente, por não ser possível decidir apenas lendo o código: `readseeds2.py` e
`virus_hunter.py` produzem resultados científicos materialmente distintos, e a escolha
determina qual comportamento a refatoração deve preservar.

Quatro linhas de evidência foram levantadas desde então e resolvem a questão.

### E1 — `virus_hunter.py` implementa o método publicado do grupo

Deng X, Naccache SN, Ng T, Federman S, Li L, Chiu CY, Delwart EL.
*An ensemble strategy that significantly improves de novo assembly of microbial genomes
from metagenomic next-generation sequencing data.*
**Nucleic Acids Research 43(7):e46, 2015.** PMC4402509.

O artigo é do próprio autor do código, com Delwart e Chiu, e estabelece **`SAVaC`**
(SOAPdenovo2 + ABySS + MetaVelvet + ABySS particionado + Cap3) como a melhor combinação.

| Parâmetro do artigo | `virus_hunter.py` | `readseeds2.py` |
|---|---|---|
| Combinação `SAVaC` | `assembly_para='SAVa'` → `AddPipe('SAVaC', sf)` — **literal** ([2164-2167](../../script/virus_hunter.py#L2164-L2167)) | conceito ausente; inclui **MIRA**, avaliado e **excluído** pelo artigo |
| Filtro de 300 bp antes da montagem final | `contigLength1 = 300` ✓ | `contigLength1 = 150` ✗ (é o `CON_LEN_DBG`, filtro anterior) |
| k = 31 | `31` ✓ | `31` ✓ |
| Chunks de 100K leituras | `partition.py … 100000` ✓ | `100000` ✓ |
| Phred 10 | `phred=10` ✓ | ✓ |

Quatro parâmetros coincidem com `virus_hunter.py`; `readseeds2.py` diverge em dois e usa
um assembler que o artigo descartou.

### E2 — `virus_hunter` é o módulo canônico do código

[`firstpage.py:68`](../../script/firstpage.py#L68), no nível do módulo:

```python
from virus_hunter import readSeeds2
```

`firstpage.py` gera o relatório final e é chamado pelos pipelines **dos dois**
orquestradores. É de `virus_hunter` que ele importa.

### E3 — Forense do bytecode

Existe `script/virus_hunter.pyc` e **nenhum** `readseeds*.pyc`. Python 2 grava `.pyc` ao
**importar** um módulo — prova de que `firstpage.py` executou de fato, importando
`virus_hunter`.

O cabeçalho do `.pyc` traz a data do fonte compilado: **2020-07-08 22:18 UTC**, quatro
dias antes do upload do repositório (2020-07-12). Magic 62161 (Python 2.6). Ou seja:
`virus_hunter.py` foi modificado e importado em execução real imediatamente antes do
upload.

### E4 — Desenvolvimento assimétrico

Doze workers substantivos são exclusivos de `virus_hunter` (DIAMOND, CLARK, rota NT,
HMMER, `tally`, `mergeTable`, `annotate_contig`…), contra dois de `readseeds2`.

### Evidência em sentido contrário, e por que é mais fraca

- **`script/readme.txt` aponta para `readseeds2.py`.** Mas sua primeira linha diz
  *"next update is Jan 2013"* — **o documento é de 2012**, cerca de oito anos anterior ao
  código. Não descreve a prática vigente.
- **O trabalho do grupo em jan/2025 usou `readseeds2.py`.** Explicável por conveniência
  técnica: é o que não trava no import. Ver a correção em Consequências.

## Decisão

1. **`virus_hunter.py` é a referência científica** da refatoração. O comportamento a ser
   preservado é o dele.
2. **A configuração de referência é `doAssembly='denovo'`** (`SAVa` → `SAVaC`), conforme
   Deng et al. 2015 — **não** o `'no'` do estado commitado.
3. `readseeds2.py`, `readseeds_denovo.py`, `readseeds_cloud.py` e `readseeds.py` passam a
   **legado**. Serão removidos em incremento próprio, depois de etiquetados.
4. Esta decisão **não** cobre a escolha do filtro NR, tratada em
   [ADR-0005](0005-nr-filter-strategy.md).

## Consequências

- **O estado commitado do repositório não é a configuração de produção.** Com
  `doAssembly='no'`, o pipeline não monta contigs, contrariando o método publicado. O
  "não determinado" registrado em [`pipeline.md`](../pipeline.md) fica resolvido: é
  estado de teste.
- **Correção a uma afirmação anterior.** Foi documentado que `readseeds2.py` é o único que
  roda fora do cluster. Está incompleto: o pipeline gerado por ele chama `firstpage.py`,
  que importa `virus_hunter` no nível do módulo e dispara `serverInfo()` → SSH para 20
  nós. `readseeds2.py` *gera* scripts sem cluster, mas a etapa final de relatório não
  executa sem ele. Nenhum dos dois é utilizável fora do cluster hoje.
- **O SSH em tempo de import passa a ser bloqueador de prioridade alta** (K10). Enquanto
  existir, a referência não pode ser importada nem testada localmente. Deve ser a primeira
  mudança de código, e é uma refatoração sem alteração de comportamento científico.
- O trabalho de jan/2025 sobre `readseeds2.py` não será aproveitado, de acordo com
  [ADR-0002](0002-working-base-and-fork.md).
- Se surgir evidência de que análises do grupo usaram `readseeds2.py` — a seção de métodos
  de um artigo, ou um `run.log` com `n=140` / `contigLength2=300` — esta ADR deve ser
  revista.
