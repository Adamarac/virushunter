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

### 2. Apenas um deles roda fora do cluster

`virus_hunter.py` dispara SSH para 20 servidores no momento do import
([linha 205](../script/virus_hunter.py#L205)). Sem o cluster original, ele nem inicia.
`readseeds2.py` não tem essa chamada.

Isso provavelmente explica a escolha do trabalho anterior do grupo (jan/2025, no fork
`amphybio`), que ajustou `readseeds2.py` para rodar fora do cluster. **É uma explicação de
conveniência técnica, não necessariamente de preferência científica** — e essa distinção
importa para a decisão.

### 3. O filtro NR mais forte está no menos capaz

`blast_filter_NR.py` (usado por `readseeds2.py`) exige que o hit viral tenha e-value
melhor que o do melhor hit não-viral — critério estatisticamente defensável.
`diamond_filter_NR.py` (usado por `virus_hunter.py`) apenas descarta queries cujo melhor
hit não seja viral, sem comparar magnitudes.

Ou seja: o orquestrador com o ferramental **mais moderno** usa o filtro **mais fraco**, e
a rota mais forte está explicitamente comentada
([`virus_hunter.py:2208`](../script/virus_hunter.py#L2208)).

---

## O que resolveria a decisão

A escolha não pode ser feita apenas por leitura de código. As evidências que faltam:

1. **Qual foi usado nas análises publicadas do grupo?** A seção de métodos de qualquer
   artigo produzido com este pipeline responde diretamente. É a evidência mais forte.
2. **Existe algum `run.log` de execução real preservado?** Ele registra os parâmetros
   efetivamente usados e permite identificar o orquestrador pelos valores (`n=140` vs
   `n=50`, `contigLength2=300` vs `1500`).
3. **A montagem é considerada obrigatória pelo grupo?** Se sim, o estado commitado de
   `virus_hunter.py` (`doAssembly='no'`) é um estado de teste, não de produção — e a
   comparação muda.
4. **O modo é *paired-end* ou *single-end* nas amostras atuais?** Determina qual conjunto
   de parâmetros faz sentido.

## Alternativa: não escolher nenhum

Uma terceira via é tratar ambos como legado e **definir o pipeline alvo explicitamente**,
etapa por etapa, escolhendo para cada uma o comportamento desejado com decisão registrada.
Mais lento, porém sem herdar acidentalmente parâmetros que ninguém escolheu — e vários dos
parâmetros atuais (o `if zz<40` do trim de qualidade, o corte de 1500 bp, `n=50`) não têm
justificativa registrada em lugar nenhum.

A decisão está registrada como pendente em
[ADR-0003](decisions/0003-canonical-orchestrator.md).
