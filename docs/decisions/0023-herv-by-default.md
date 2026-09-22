# 0023 — O `HERVaa.fasta` passa a ser montado por padrão

- **Status:** Aceita
- **Data:** 2026-09-22
- **Decidido por:** Alan M

Substitui o último item das consequências da
[ADR-0022](0022-migrate-taxonomy-split.md), que registrava a opção `--gravar-herv`
desligada por padrão.

## Contexto

O `split_by_taxonomy.py` junta ao banco viral um arquivo de retrovírus endógenos humanos, o
`HERVaa.fasta`, para que eles não sejam reportados como achados. **Esse arquivo nunca
esteve no repositório**, em nenhum commit, e ninguém sabe de onde veio.

Com ele ausente, o script morre no `open()` — ou seja, na prática **o banco não era
construível**. A ADR-0022 resolveu isso com a opção `--gravar-herv`, que aproveita o fato de
o script já identificar os HERV dentro do NR e escreve esses mesmos registros no arquivo.
Mas deixou a opção desligada, para preservar a fidelidade ao original.

Na prática isso significava que o único comando que funcionava não era o comando padrão:
quem seguisse a documentação sem ler a seção de pendências batia no erro.

## Alternativas consideradas

**Ligar a opção sempre.** Simples, mas sobrescreveria um `HERVaa.fasta` curado, que é
justamente a escolha mais fiel quando existe.

**Manter desligada e só documentar melhor.** Preserva a fidelidade, mas mantém o comando
padrão quebrado — é documentação compensando um padrão ruim.

**Ligar, com o arquivo existente tendo precedência.** Escolhida.

## Decisão

Não há mais opção de ligar. A etapa `proteins` decide sozinha:

| Situação | O que faz |
|---|---|
| existe `HERVaa.fasta` na pasta | usa o que está lá, intocado |
| não existe | monta a partir dos HERV que achar no NR |
| `--refazer-herv` | refaz mesmo existindo |

O script imprime qual caminho tomou. A troca nunca é silenciosa.

`--gravar-herv` deixou de existir; `--refazer-herv` entrou no lugar, para o caso de querer
atualizar o conjunto junto com o NR.

## Verificação

Sobre o mesmo fixture da ADR-0022, contra a saída do `nr_virus3.py` original rodado em
`python:2.7-slim`:

| Cenário | Resultado |
|---|---|
| **arquivo presente** (o caso fiel) | os **seis arquivos idênticos** ao Python 2; `HERVaa.fasta` intocado |
| **arquivo ausente** | cinco idênticos; só `virus.fa` muda, e só no bloco HERV |
| **`--refazer-herv`** | sobrescreve; mesmo conjunto do cenário anterior |

Ou seja: quando existe um arquivo curado, **o comportamento é o do original, byte a byte**.
A diferença aparece exatamente no caso em que o original não rodaria.

## Consequências

- O comando documentado para construir os bancos volta a ser o comando que funciona.
- **Muda o comportamento científico no caso do arquivo ausente**: onde antes havia falha,
  agora entra no banco viral o conjunto de HERV que o próprio NR traz. É o mesmo critério de
  taxonomia que o script já usa (`Human endogenous retroviruses`, táxon 206037).
- **O risco fica registrado:** um conjunto de HERV mais amplo que o original pode absorver
  leituras de retrovírus exógenos genuínos, que deixariam de ser reportadas — um falso
  negativo. Quem tiver o arquivo original deve deixá-lo na pasta; ele tem precedência.
- **Qual conjunto de HERV usar continua sendo decisão do grupo.** O que esta ADR decide é só
  o que acontece quando não há escolha feita.
