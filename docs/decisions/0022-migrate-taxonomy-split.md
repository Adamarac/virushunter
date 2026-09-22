# 0022 — Migrar o separador por taxonomia

- **Status:** Aceita
- **Data:** 2026-09-22
- **Decidido por:** Alan M

## Contexto

Os bancos de dados são o último bloqueio do projeto, e descobriu-se que **baixá-los não
basta**: o pipeline depende de cabeçalhos com a taxonomia embutida
(`species$..:genus$..:family$..:category$..`), e de um prefixo `VIRUS_`/`PHAGE_`/`NV_` no
banco do DIAMOND.

Quem produzia isso era `nr_virus3.py` — 457 linhas de Python 2, removidas na poda
([ADR-0020](0020-prune-to-the-migrated-version.md)). Sem ele, o
[`build_report.py`](../../script/report/build_report.py) cai no `except` e **todo hit vira
`NA` em silêncio**, e o [`filter_nr.py`](../../script/search/filter_nr.py) perde o critério
do prefixo.

Das três variantes no histórico (`nr_virus.py`, `2`, `3`), a terceira é a única que usa
**accession** em vez de GI — ou seja, já é posterior à descontinuação dos GIs em 2016. Foi
a escolhida.

## Decisão

Migrado para [`script/database/split_by_taxonomy.py`](../../script/database/split_by_taxonomy.py),
com o nome dizendo o que faz. Não entra no fecho do `Snakefile`: é ferramenta de
manutenção, rodada quando os bancos são reconstruídos.

### Conversão mecânica

`print >>f, x` → `print(x, file=f)`; `d.has_key(k)` → `k in d`;
`gzip.open(..., 'rb')` → `'rt'`, porque em Python 2 o modo binário entregava `str` e todo o
processamento adiante é de texto; `filter = filter2.keys()` deixou de sombrear a função
`filter`.

### Três mudanças além do mecânico

**1. A memória, que impedia o script de rodar.** `loadTax()` carregava
`prot.accession2taxid` inteiro num dicionário. Hoje esse arquivo tem 11 GB comprimidos e
mais de um bilhão de entradas: em Python isso custa **centenas de GB de RAM**. O script não
rodaria em máquina alguma.

O mapa só é consultado quando o `[organismo]` do cabeçalho não resolve pelo nome. Então
passou a haver duas passagens: a primeira descobre quais accessions o arquivo de entrada
cita, a segunda lê o mapa guardando apenas esses.

Isso é **provadamente equivalente** — filtrar as chaves de um dicionário consultado por
chave não muda resultado nenhum — e foi verificado: as duas modalidades produzem saída
idêntica sobre o mesmo fixture. A original segue disponível em `--mapa-inteiro`.

**2. A duplicação entre as duas funções.** `addTaxon` e `addTaxonDNA` eram 136 e 142 linhas
com 44 linhas de diferença, quase toda ela em qual arquivo escrever. A classificação — ler
a linhagem, decidir vírus/fago/HERV, montar o rótulo — virou uma função `classifica()`
usada pelas duas. É o mesmo tipo de fusão feita nos filtros NR
([ADR-0021](0021-organize-scripts-by-stage.md)).

**3. O fluxo deixou de ser editado à mão.** No original, o que rodava eram as últimas
linhas do arquivo, e **quase todas estavam comentadas** — só a etapa de DNA estava ativa.
Usar o script exigia descomentar linhas. Agora há duas etapas explícitas,
`proteins` e `dna`, e os `os.system` com `segmasker`/`makeblastdb`/`diamond makedb` saíram
para [`docs/databases.md`](../databases.md): são chamadas de ferramenta externa, e neste
projeto ferramentas vêm da configuração.

## Verificação

Sobre um fixture sintético construído para exercitar cada caminho — linhagem viral
completa, fago, HERV, bactéria, entrada humana-e-viral, reserva por accession, entrada sem
taxonomia, accession duplicado e o filtro de nomes repetidos:

| Checagem | Resultado |
|---|---|
| Analisa e compila em Python 3 | sim |
| Restos de Python 2 (`print >>`, `has_key`, `xrange`, `iteritems`) | zero |
| Nomes indefinidos (varredura por `ast`) | zero |
| Duas modalidades de carga do mapa | **saída idêntica** |
| Etapa `proteins` | `virus.fa` 5, `phage.fa` 1, `diamond.fa` 6, `human.virome.fa` 2 |
| Etapa `dna` | `virus.DNA.fa` com a linhagem correta |

Os rótulos saem no formato que o `build_report.py` espera, com `category$ssRNA_viruses`
derivada da posição na linhagem — a mesma que aparece no comentário do código original.

### Comparação com o original

Rodado o `nr_virus3.py` original em `python:2.7-slim`, sobre o mesmo fixture, com as
funções intocadas e apenas o driver do fim completado com a sequência que os comentários
descreviam. **Os sete arquivos saem idênticos**: `virus.fa`, `virus.tmp.fa`, `phage.fa`,
`diamond.fa`, `human.virome.fa`, `virus.DNA.fa` e `tax_tree.txt`.

A comparação encontrou uma divergência real, que só ela revelaria: o `print` do Python 2
**não emitia o espaço separador quando o item anterior terminava em tabulação** — a regra
de *softspace*, que o Python 3 não tem. O `tax_tree.txt` saía com um espaço a mais por
nível de indentação. Corrigido montando a linha à mão.

Nenhum banco era afetado por isso; só o despejo diagnóstico da árvore. Mas é exatamente o
tipo de diferença silenciosa que justifica comparar byte a byte em vez de confiar na
leitura.

### Limites

**Ordem de dicionário.** O filtro de nomes repetidos itera sobre as quatro chaves. Em
Python 2 essa ordem era arbitrária; aqui é a de inserção. Só faria diferença se um mesmo
cabeçalho citasse dois daqueles vírus, o que é improvável — mas é o mesmo tipo de mudança
forçada registrada na [ADR-0010](0010-dict-ordering-behaviour-change.md).

**Os `except:` nus foram mantidos.** São a forma do original e transformá-los em falha alta
é decisão separada, registrada em [K5](../known-issues.md). Num código científico que não
tenho como executar de verdade, preservar o comportamento vale mais.

## Consequências

- Os bancos passam a ser construíveis, o que destrava o único bloqueio real que restava.
- Registrado [K37](../known-issues.md): `diamond.fa` recebe **identificadores duplicados**,
  porque o contador reinicia entre as duas chamadas de `addTaxon`. Herdado, não introduzido.
  Não quebra o `filter_nr.py`, que só lê o prefixo até o primeiro `_`.
- O `HERVaa.fasta` continua sem origem conhecida, mas deixou de ser bloqueio: a opção
  `--gravar-herv` monta o arquivo a partir dos HERV que o próprio script encontra no NR,
  pelo mesmo critério de taxonomia. Desligada por padrão, e recusa sobrescrever um arquivo
  existente — o comportamento sem ela segue idêntico ao original, verificado.
  **Qual conjunto de HERV usar continua sendo decisão do grupo**: o arquivo original pode
  ter sido curado à mão.
