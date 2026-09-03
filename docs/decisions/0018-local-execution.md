# 0018 — Execução local: sem cluster, ferramentas no PATH

- **Status:** Aceita
- **Data:** 2026-08-15
- **Decidido por:** Alan M

## Contexto

`config/default.yaml` foi extraído dos literais do código original ([ADR-0015](0015-declarative-configuration.md)),
o que significa que descrevia o cluster do grupo em 2015: caminhos absolutos sob
`/mnt/cluster/xdeng/`, 48 threads, 50 fatias de query (uma por nó) e uma lista de 20 nós
`bsidna*` alcançados por SSH.

Nada disso existe na máquina onde o pipeline vai rodar. O ambiente real é **uma máquina
local com múltiplos núcleos, sem cluster e sem nenhuma das ferramentas externas
instaladas**.

Isso era mais que inconveniente: a configuração *mentia*. Um `snakemake` ali falharia
apontando `/mnt/cluster/...`, sugerindo problema de montagem de disco em vez do que
realmente é — ferramenta ausente e banco não baixado.

## Decisão

`config/default.yaml` passa a descrever a execução local.

**Ferramentas** — nomes de comando, procurados no `PATH`:

```yaml
tools:
  blastx: "blastx"          # em vez de /mnt/cluster/xdeng/tools/ncbi-blast-2.2.31+/bin/blastx
  diamond: "diamond"
  soapdenovo: "SOAPdenovo-63mer"
```

Quem instalar uma ferramenta fora do `PATH` troca uma linha. Os nomes de binário foram
corrigidos onde o nome da chave não era o nome real do executável (`SOAPdenovo-63mer`,
`meta-velvetg`, `abyss-pe`, `Ray`).

**Bancos de dados** — apontam para `db/` no diretório de trabalho, com aviso explícito de
que os arquivos não vêm com o projeto e precisam ser obtidos:

```yaml
databases:
  virus_protein: "db/virus_mask"
```

Isso não resolve o problema — os bancos continuam ausentes — mas faz a falha dizer a
verdade.

**`cluster.enabled: false`.** A seção fica, porque `virus_hunter.py` ainda lê
`cluster.high_memory_nodes`, mas deixa de afirmar que há um cluster.

**`tools.scripts_dir` relativo** é resolvido contra a raiz do projeto, não contra o
diretório de trabalho da amostra. Sem isso, `script/` viraria
`<pasta-da-amostra>/script/` e nenhuma regra encontraria os scripts, porque o Snakemake
roda com `--directory` apontando para a amostra.

## Preservação da referência congelada

`tests/reference/expected*/` foi capturada com os valores do cluster. Trocar
`default.yaml` tornaria a referência irreproduzível — perda séria, porque ela é a única
especificação executável do pipeline original que sobrou.

Os valores originais foram movidos para **`config/cluster-legacy.yaml`**:

```
snakemake --configfile config/cluster-legacy.yaml
```

Não é máquina nova: é um arquivo de sobreposição usando o mecanismo que já existia.

## Alternativas consideradas

**Deixar `default.yaml` como estava e criar `config/local.yaml`.** Preservaria a referência
sem esforço. Custo: o padrão continuaria sendo um ambiente que ninguém tem, e todo comando
precisaria de `--configfile`. O padrão deve ser o caso real.

**Detectar as ferramentas em tempo de execução (`shutil.which`).** Custo: esconde a
ausência em vez de reportá-la, e adiciona lógica para um problema que uma linha de
configuração resolve.

## Consequências

- Um `snakemake` local falha dizendo `blastx: command not found` ou `db/virus_mask` ausente
   — diagnóstico correto, em vez de um caminho de cluster inexistente.
- A referência congelada continua reproduzível, mas exige `--configfile
  config/cluster-legacy.yaml`. Quem esquecer compara contra a coisa errada. Não há
  verificação automática que pegue isso — as que existiam foram removidas a pedido.
- **`compute.threads: 48` foi mantido.** É valor de nó de cluster e provavelmente alto para
  a máquina local, mas eu não sei quantos núcleos ela tem e não vou inventar. Ajuste antes
  do primeiro uso: afeta desempenho, e nos montadores pode afetar o resultado.
- **`compute.query_splits: 50` foi mantido.** Significava "uma fatia por nó"; localmente
  virou apenas o tamanho do lote. Continua funcionando e mexer nele mudaria a estrutura de
  arquivos intermediários sem ganho claro.
- Nada disto foi executado. Continua valendo a [ADR-0009](0009-no-execution-environment.md):
  a validação foi por resolução de DAG, não por execução.
