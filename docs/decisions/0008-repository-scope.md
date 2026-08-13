# 0008 — Escopo do repositório

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

O repositório é a caixa de ferramentas de um laboratório inteiro depositada em um único
diretório plano, não um pipeline. Dos 155 arquivos `.py`, o fecho de alcançabilidade a
partir de `virus_hunter.py` (a referência, [ADR-0004](0004-virus-hunter-as-reference.md))
tem **46 arquivos**. Os demais incluem pipelines completos de RNA-seq, ChIP-seq e chamada
de variantes.

Isso é o principal obstáculo para alguém novo entender o projeto: não há como distinguir o
que importa do que não importa sem fazer análise de alcançabilidade. Também é o que torna
difícil avaliar qualquer proposta de reorganização — a maior parte do que se veria numa
listagem de diretório é ruído.

[ADR-0004](0004-virus-hunter-as-reference.md) já havia declarado os demais orquestradores
como legado, a serem removidos "em incremento próprio, depois de etiquetados".
[K24](../known-issues.md) mostrou depois que três deles passam o argumento errado ao filtro
NR e falham desde a correção de [ADR-0007](0007-inert-evalue-threshold.md).

## Alternativas consideradas

**Remover pelo fecho de alcançabilidade.** Critério objetivo, mas errado: descartaria os
scripts de construção de banco (`nr_virus*.py`, `acc_tax*.py`, `nt_extract_bac.py`), que não
são invocados pelo pipeline em execução mas são essenciais à reprodutibilidade e estão
documentados em `script/readme.txt`.

**Mover para um diretório `attic/`.** Mantém tudo visível sem poluir a raiz. Descartada: o
Git já é o mecanismo de recuperação, e um `attic/` só adia a decisão.

**Remover por classificação de domínio, usando alcançabilidade como trava.** Remove o que
pertence comprovadamente a outra área científica, e verifica mecanicamente que nada do
fecho de código vivo saiu junto.

## Decisão

Remover por classificação de domínio, com trava de alcançabilidade. **80 arquivos removidos:**

| Grupo | Arquivos |
|---|---|
| RNA-seq / expressão | 9 |
| ChIP-seq / picos / wig | 15 |
| `ChromSizes/` (só ChIP-seq/RNA-seq) | 26 |
| Variantes / GATK / pileup | 12 |
| Plataforma 454 (não-Illumina) | 3 |
| Orquestradores legados (ADR-0004) | 4 |
| Depreciados pelo próprio nome | 2 |
| Anotação de genoma avulsa (`K4705*`, `gb2gtf.py`) | 6 |
| Artefato de build (`virus_hunter.pyc`) | 1 |
| Órfãos remanescentes (`bowtie2svg.py`, `testKmer.py`) | 2 |

Restam **110 arquivos `.py`** — os 46 do fecho de código vivo mais scripts de construção de
banco e utilitários virais que, na dúvida, foram mantidos.

Acrescentados `.gitignore` (artefatos gerados em tempo de execução) e `.gitattributes`
(normalização de fim de linha para LF — o pipeline roda em Linux e os scripts são
consumidos por `sh`).

### Verificações executadas

1. **Trava de alcançabilidade:** nenhum dos 46 arquivos do fecho de código vivo estava na
   lista de remoção.
2. **Referências pendentes:** após a remoção, nenhum script restante referencia, em código
   vivo, um arquivo que deixou de existir. Isso revelou dois órfãos (`bowtie2svg.py`,
   `testKmer.py`), removidos junto.
3. **Testes:** `check_no_import_side_effects.py` e `check_argv_numeric_comparison.py`
   continuam passando.

## Consequências

- **Recuperação.** Tudo permanece na tag `legacy-2020`:
  ```
  git show legacy-2020:script/RNASeq.py
  ```
  Nada foi perdido; o histórico é o mecanismo de recuperação, conforme a alternativa
  escolhida.
- Uma listagem de `script/` passa a mostrar majoritariamente o pipeline viral. A proposta de
  reorganização em diretórios fica avaliável.
- Os orquestradores legados saíram, então [K8](../known-issues.md) e [K24](../known-issues.md)
  deixam de ser problemas ativos.
- **Não foi feita separação por responsabilidade** — `script/` continua plano, com 110
  arquivos. Este incremento removeu o que não pertence; organizar o que pertence é trabalho
  distinto, e depende da estrutura de diretórios proposta em `docs/architecture.md`, ainda
  não decidida.
- Ficaram arquivos de classificação ambígua (`iupac.py`, `fusion.sh`, `restore_qual.py`,
  `sam2fq_BASV.py`, entre outros). Mantidos deliberadamente: na dúvida, preservar. Uma
  segunda passada pode reavaliá-los com mais contexto do grupo.
