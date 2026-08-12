# Os orquestradores concorrentes

O repositório contém **cinco** variantes do mesmo orquestrador. Não são especializações —
são cópias divergentes, editadas manualmente ao longo do tempo.

| Arquivo | Linhas | Observação |
|---|---|---|
| [`virus_hunter.py`](../script/virus_hunter.py) | 2.233 | Superset mais recente |
| [`readseeds2.py`](../script/readseeds2.py) | 997 | Apontado pelo `script/readme.txt` |
| [`readseeds_denovo.py`](../script/readseeds_denovo.py) | 898 | Variante focada em montagem |
| [`readseeds_cloud.py`](../script/readseeds_cloud.py) | 541 | Variante "cloud" |
| [`readseeds.py`](../script/readseeds.py) | 228 | Provável ancestral |

Evidência da decadência por cópia: `readseeds2.py` define `soap_single()` **duas vezes**
(linhas 421 e 594). A segunda sobrescreve silenciosamente a primeira — um sintoma clássico
de merge manual entre forks.

Este documento compara os dois candidatos reais a referência.

---

## Comparação funcional

| Aspecto | `readseeds2.py` | `virus_hunter.py` |
|---|---|---|
| **Montagem** | **Sempre executa** — SOAP + MetaVelvet + ABySS + ABySS particionado + MIRA → CAP3. Sem flag para desligar | **Opcional** (`doAssembly`); no estado commitado `'no'` → **não monta** |
| **SPAdes** | ausente | presente (rotulado "trinity") |
| **DIAMOND** | ausente | presente (triagem e filtro NR) |
| **CLARK** | ausente | presente (opcional) |
| **Rota NT** | ausente | presente (opcional) |
| **HMMER + vFam** | ausente | presente (`doHmmer` / `doMyth`) |
| **Remontagem cruzada** | ausente | presente |
| **Filtro NR** | `blast_nr` → `blast_filter_NR.py` (**compara e-values**) | `diamond_nr` → `diamond_filter_NR.py` (lista negra); rota BLAST comentada |
| **Escalonador** | não usa `schedule2.py` | usa `schedule2.py` para BLAST e bowtie |
| **`serverInfo()` no import** | **não** | **sim** — SSH para 20 nós ao importar |
| **Senha em texto claro / `chmod 777`** | **não tem** | 5 ocorrências |
| **Caminhos de ferramenta** | 7 | 17 |

### Parâmetros científicos

| Parâmetro | `readseeds2.py` | `virus_hunter.py` | Razão |
|---|---|---|---|
| `n` (fatias) | 140 | 50 | — |
| `length` (leitura p/ BLAST) | 100 | 50 | 2× |
| `contigLength1` (antes do CAP3) | 150 | 300 | 2× |
| `contigLength2` (antes do BLAST) | 300 | 1500 | **5×** |
| `myslen` (contig "mystery") | 1200 | 1000 | — |
| `thread` | 8 | 48 | 6× |
| `pair` | `True` | `False` | — |

---

## As três conclusões que importam

### 1. Não são o mesmo pipeline com features diferentes

Eles produzem **resultados científicos materialmente distintos**:

- `readseeds2.py` sempre monta contigs; `virus_hunter.py`, no estado commitado, não monta.
- `readseeds2.py` usa o filtro NR por comparação de e-values; `virus_hunter.py` usa lista
  negra por prefixo de *subject*.
- O corte de contig antes do BLAST difere em 5×.
- Um roda em modo *paired-end*, o outro em *single-end*.

Escolher entre eles **é escolher qual comportamento científico será preservado**. Não é
uma decisão de engenharia.

### 2. Nenhum dos dois roda fora do cluster

`virus_hunter.py` dispara SSH para 20 servidores no momento do import
([linha 205](../script/virus_hunter.py#L205)). Sem o cluster original, ele nem inicia.
`readseeds2.py` não tem essa chamada — mas **isso não o torna independente do cluster**.

O pipeline gerado por `readseeds2.py` chama `firstpage.py` na etapa final de relatório
([`readseeds2.py:993`](../script/readseeds2.py#L993)), e
[`firstpage.py:68`](../script/firstpage.py#L68) faz, no nível do módulo:

```python
from virus_hunter import readSeeds2
```

Importar `firstpage` importa `virus_hunter`, que executa `serverInfo()` e dispara o SSH.
`readseeds2.py` **gera** os scripts sem cluster; o pipeline gerado não **termina** sem ele.

Isso explica o alcance do trabalho anterior do grupo (jan/2025, no fork `amphybio`): foi
possível avançar na geração dos scripts, não na execução completa. É conveniência técnica,
não preferência científica.

O corolário é que remover o efeito colateral de import (K10) é pré-requisito para
qualquer execução local, independentemente do orquestrador escolhido.

### 3. O filtro NR mais forte está no menos capaz

`blast_filter_NR.py` (usado por `readseeds2.py`) exige que o hit viral tenha e-value
melhor que o do melhor hit não-viral — critério estatisticamente defensável.
`diamond_filter_NR.py` (usado por `virus_hunter.py`) apenas descarta queries cujo melhor
hit não seja viral, sem comparar magnitudes.

Ou seja: o orquestrador com o ferramental **mais moderno** usa o filtro **mais fraco**, e
a rota mais forte está explicitamente comentada
([`virus_hunter.py:2208`](../script/virus_hunter.py#L2208)).

---

---

## Como a decisão foi resolvida

A questão foi decidida a favor de `virus_hunter.py` — ver
[ADR-0004](decisions/0004-virus-hunter-as-reference.md) para a evidência completa. Em
resumo:

1. **`virus_hunter.py` implementa o método publicado.** Deng et al.,
   *Nucleic Acids Research* 43(7):e46, 2015 (PMC4402509), do próprio autor com Delwart e
   Chiu, estabelece `SAVaC` como a melhor combinação de assemblers. O código traz
   `assembly_para='SAVa'` → `AddPipe('SAVaC', sf)` literalmente, além do corte de 300 bp,
   k=31 e partições de 100K leituras — todos coincidentes. `readseeds2.py` diverge em dois
   parâmetros e usa MIRA, que o artigo avaliou e excluiu.
2. **`firstpage.py` importa de `virus_hunter`**, não de `readseeds2`.
3. **`virus_hunter.pyc` está commitado e nenhum `readseeds*.pyc` está.** Python 2 só grava
   `.pyc` ao importar; a data do fonte embutida é 2020-07-08, quatro dias antes do upload.
4. **Doze workers substantivos são exclusivos de `virus_hunter`**, contra dois de
   `readseeds2`.

`script/readme.txt` aponta para `readseeds2.py`, mas sua primeira linha diz
*"next update is Jan 2013"* — o documento é de 2012 e não descreve a prática vigente.

### Consequência

A configuração de referência é `doAssembly='denovo'`, e não o `'no'` do estado commitado:
**o repositório foi publicado em estado de teste**, não na configuração de produção.

Permanece em aberto, como decisão separada, qual filtro contra NR adotar —
ver [ADR-0005](decisions/0005-nr-filter-strategy.md). Vários parâmetros atuais
(o `if zz<40` do trim de qualidade, o corte de 1500 bp, `n=50`) continuam sem
justificativa registrada e devem ser revisados individualmente, não herdados por omissão.
