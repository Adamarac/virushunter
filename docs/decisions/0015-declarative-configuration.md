# 0015 — Configuração declarativa

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

Todo parâmetro do pipeline era um literal dentro de `script/virus_hunter.py`: 38 no bloco
`__main__` e 29 caminhos absolutos em nível de módulo. Rodar uma análise com outro limiar
significava **editar o código-fonte**. É o [K9](../known-issues.md), e é a razão de nenhum
resultado poder ser acompanhado dos parâmetros que o produziram.

Duas circunstâncias tornaram a extração urgente:

1. **A execução passou a ser local.** Os valores atuais foram dimensionados para um nó do
   cluster — 48 threads, 50 fatias de query, memória vinda do nó — e quase certamente
   precisam mudar. Sem configuração, mudar significa editar código.
2. **O Snakemake lê YAML.** As regras precisarão dos mesmos valores, e mantê-los em duas
   fontes garantiria divergência.

## Decisão

Extrair tudo para `config/default.yaml`, carregado por `virushunter.config`.

**Os valores reproduzem exatamente os literais anteriores.** Isso não é conservadorismo: é
o que permite provar que a extração não mudou nada.

O carregador aceita um arquivo de sobreposição parcial — só as chaves que mudam — e
valida forma, não mérito. Chaves obrigatórias, tipos, modos válidos de montagem e de fago,
`threads`/`query_splits` positivos, e `evalue` numérico. **Não** valida se um limiar faz
sentido científico: nada aqui sabe o que é sensato, e fingir que sabe esconderia a decisão
atrás de um schema.

`bool` é rejeitado onde se espera `int`, porque `bool` é subclasse de `int` e `true`
passaria como "1 thread".

### Provado nos dois sentidos

- **A extração não mudou nada:** `verify.sh` compara os scripts gerados byte a byte com a
  referência congelada e passa.
- **A config realmente controla:** alterar `params.evalue` de `0.01` para `0.001` **no
  YAML** faz `verify.sh` falhar. Sem essa segunda verificação, uma config ignorada pelo
  código passaria por funcionando.

### O que ficou documentado no próprio YAML

Comentários registram onde um valor é suspeito mas foi preservado:

- `steps.assembly.mode: "no"` é o estado commitado e **não** é a configuração de produção —
  o método publicado exige `denovo` ([ADR-0004](0004-virus-hunter-as-reference.md)).
- `steps.nt_route` alimenta uma rota cujas contagens são não confiáveis ([K2](../known-issues.md)).
- `compute.*` está dimensionado para um nó de cluster que não existe mais.
- A seção `cluster` está marcada como **legado**: existe só para reproduzir a saída do
  gerador atual, e será descartada na migração para Snakemake.

## Consequências

- Uma execução passa a ser descrita por um arquivo versionável, que pode acompanhar o
  resultado — pré-requisito de reprodutibilidade que [K6](../known-issues.md) e
  [K9](../known-issues.md) apontavam.
- Ajustar o pipeline para a máquina local vira edição de YAML.
- `pyyaml` entra como dependência. Considerei TOML via `tomllib` (stdlib, sem dependência),
  mas o Snakemake lê YAML nativamente e converter depois seria trabalho perdido.
- **A validação não cobre caminhos.** Nada verifica que os binários e bancos existem; hoje
  todos apontam para o cluster e nenhum existe localmente. Falharia em execução, não no
  carregamento. Melhoria natural quando os caminhos locais forem definidos.
- Os workers **não** leem a config — continuam recebendo tudo por linha de comando, que é o
  contrato deles. Só o gerador lê.

### Dois defeitos que este incremento revelou

**A descoberta da config estava frágil.** A primeira versão derivava o caminho de
`__file__`, o que só funciona a partir de uma árvore de código: instalado, o módulo fica em
`site-packages` e a config não está três diretórios acima. Agora há busca explícita — cwd,
árvore de código, ao lado do módulo — e `VIRUSHUNTER_CONFIG` sobrepõe tudo.

**O smoke test usava lista negra.** Ele marcava como suspeitas apenas exceções específicas
(`NameError`, `AttributeError`, `ImportError`…), então qualquer modo de falha novo passava
como esperado. Foi exatamente o que aconteceu: `ConfigError` é `ValueError`, e o teste
reportou 46 arquivos limpos enquanto `virus_hunter.py` e `firstpage.py` morriam por config
não encontrada.

Invertido para **lista branca das falhas esperadas**. Isso imediatamente expôs cinco casos
que a lista negra escondia — `ValueError` de desempacotamento de `sys.argv`, escrita em
sistema de arquivos somente-leitura, e o `virus_hunter.py` alcançando `serverInfo()`. Cada
um foi analisado e admitido explicitamente, com o motivo no código. Uma lista branca torna
cada exceção uma decisão; uma lista negra torna cada omissão um silêncio.
