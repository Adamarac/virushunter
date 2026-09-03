# 0020 — Podar o repositório para a versão migrada

- **Status:** Aceita
- **Data:** 2026-08-15
- **Decidido por:** Alan M

## Contexto

Pedido: deixar apenas o que de fato é usado pela versão migrada, e reduzir os comentários.

A condição posta antes era que 100% do que ficasse já estivesse portado. Ela é verificável,
e foi verificada.

## Como o conjunto "usado" foi determinado

Não por leitura nem por intuição: por **fecho transitivo** a partir do `Snakefile`,
computado por um script, com três correções ao longo do caminho — cada uma teria causado
perda de arquivo usado ou retenção de lixo.

1. **Comentários contavam como referência.** A primeira versão casava nomes de arquivo em
   qualquer lugar do texto, inclusive dentro de comentários. Um comentário meu citando
   `virus_hunter.py` mantinha o orquestrador inteiro vivo. Corrigido usando `ast` para os
   arquivos que parseiam e um removedor de comentários para os demais. O fecho caiu de 54
   para 24 arquivos.

2. **Nomes duplicados em subpasta.** `script/ensembleAssembly_1/` continha cópias de
   `faLenFilter.py`, `fqLenFilter.py` e `partition.py`. Como o índice era por nome com
   `rglob`, o analisador lia a cópia errada — e `partition.py` **difere em 6 linhas** entre
   as duas. Corrigido restringindo a `script/`, que é para onde `tools.scripts_dir` aponta.

3. **Referências fora do Python.** A regra `publish` copia `SCRIPTS + "*.php"` — um glob,
   invisível para a varredura. Os 6 `.php` são usados, e `cat.php` invoca `catAlignFA.py`,
   que estava marcado para exclusão. Incluídos na semente.

Resultado: **33 arquivos usados, 87 removidos**, de 120.

## Verificação

| Checagem | Resultado |
|---|---|
| Os 24 `.py` que ficam compilam em Python 3 | **24 de 24** |
| Algum arquivo mantido cita um removido? | 3 ocorrências, **todas falso positivo** — `blast_trim.py` contém a subcadeia `trim.py`, e a terceira era um comentário meu |
| Dos 85 `.py` removidos, quantos nem compilavam? | 45 |
| As 6 rotas do DAG após a remoção | 349 / 355 / 357 / 369 / 445 / 349 — **idênticas** |

Duas falhas minhas no processo, ambas detectadas antes de causar dano:

- Um laço de exclusão que **reportou 87 arquivos removidos sem remover nenhum**. Os nomes
  vinham de um arquivo escrito por Python no Windows, com CRLF; o `\r` no fim tornava todo
  caminho inexistente, e o contador incrementava fora da condição de sucesso. É o mesmo
  defeito de CRLF que já havia ocorrido nesta refatoração e estava documentado.
- Uma verificação de compilação que **passou tendo executado zero iterações**, porque o
  Python no Windows resolve `/tmp` para um lugar diferente do shell MSYS, e o arquivo de
  lista não existia onde o `grep` procurava.

## O corte de dependência que tornou isto possível

`firstpage.py` fazia `from virus_hunter import readSeeds2`. Uma linha, e por causa dela o
orquestrador legado e mais 29 scripts eram alcançáveis pela versão migrada.

`readSeeds2` tem 25 linhas úteis, lê `fastq/samples.txt` e devolve as amostras. Foi copiada
para dentro de `firstpage.py` **sem alteração** — a única linha removida foi o
`global seeds`, que só fazia sentido no módulo de origem.

Equivalência verificada por execução, não por leitura: as duas versões, sobre o mesmo
`samples.txt`, devolvem `seeds` e as chaves de `stats` idênticos.

## Redução de comentários

De **362 para 120** (de 15% para 6% das linhas). Nenhuma remoção manual: três passadas
automáticas, todas com o mesmo critério de segurança — **a AST antes e depois precisa ser
idêntica**. Comentário não afeta a AST, então qualquer diferença significaria código
quebrado. Os comentários foram localizados com `tokenize`, nunca por regex sobre o texto,
para não confundir um `#` dentro de uma string com um comentário.

O que saiu: 326 comentários que eram **código desativado**, não explicação — 54% do total
na primeira medição. Fragmentos de HTML, pedaços de script R, chamadas comentadas,
atribuições antigas.

O que ficou: os rótulos dos argumentos posicionais (`sys.argv[1] #fq file`), que são a
única documentação da interface desses scripts, e as explicações de comportamento não
óbvio.

## O que foi preservado apesar de não ser "usado"

- **`tests/reference/`** — a especificação capturada do pipeline original. Foi decisão
  explícita anterior mantê-la, e o `fixture/` é o que valida o DAG. Não seria revertida em
  silêncio por uma instrução ambígua.
- **`docs/`** — o mapa técnico. As citações a `script/` viraram texto simples; a nota em
  [`docs/README.md`](../README.md) explica como recuperá-las do histórico.
- **O procedimento dos bancos de dados**, que estava em `script/readme.txt` e nos
  comentários de `nr_virus.py`. Ambos removidos, conteúdo migrado para
  [`docs/databases.md`](../databases.md) — é o próximo bloqueio real do projeto, e perdê-lo
  seria caro.

## Consequências

- `script/` passa de 120 para 33 arquivos, todos alcançáveis e todos em Python 3.
- Um defeito corrigido de passagem: a regra `publish` copiava só `*.php`, deixando
  `tablestyle.css` e `wait.gif` de fora. O relatório publicado ficaria sem folha de estilo.
- **`blastAlias.py` invoca `blastdb_aliastool` como nome nu**, fora da configuração. O
  binário está em `tools/bin/`, mas não no `PATH`, então essa regra falha. Registrado aqui,
  não corrigido — é o mesmo padrão de `makeblastdb`, que foi para a configuração.
- O que foi removido continua no histórico. `git show 505f18b:script/<arquivo>`.
