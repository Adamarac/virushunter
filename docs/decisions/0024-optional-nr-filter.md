# 0024 — O filtro contra o NR passa a ser opcional de verdade

- **Status:** Aceita
- **Data:** 2026-09-22
- **Decidido por:** Alan M

## Contexto

A máquina onde o pipeline vai rodar (`antp`) tem 96 núcleos, 125 GB de RAM e **425 GB
livres**. O banco do DIAMOND passa de 500 GB, porque o `diamond.fa` é o NR **inteiro**
reescrito com rótulos, não só a fração viral. Ou seja: a rota padrão não cabe no disco.

Existia uma chave para isso, `steps.nr_filter`, desde a [ADR-0015](0015-declarative-configuration.md).
Ela era lida para a variável `FILTRO_NR` e **nunca usada** — `false` não mudava nada. Ver
[K38](../known-issues.md).

## Alternativas consideradas

**Só conseguir mais disco.** É a saída certa quando existe, e continua sendo a recomendação
para resultados publicáveis. Mas depende de terceiros e não resolve o caso de quem nunca vai
ter 1 TB.

**Construir o `diamond.fa` só com a fração viral.** Cabe no disco, mas destrói o filtro: ele
existe justamente para reconhecer o que é **não viral**. Um banco só de vírus faria todo
candidato parecer viral.

**Fazer a chave funcionar.** Escolhida.

## Decisão

`steps.nr_filter: false` — ou a rota `no-nr-filter` — passa a remover do DAG a busca contra
o NR e o passo que a alimenta, e o `filter_nr.py` ganha um terceiro modo, `nenhum`, que
percorre os acertos e não descarta nenhum.

O modo `nenhum` mantém o formato de saída intacto: o mesmo bloco de 11 linhas, com `-` no
campo `LNVNRE`, exatamente como o modo `diamond` já fazia. Todo o relatório adiante continua
funcionando sem saber que o filtro não rodou.

## Verificação

| Checagem | Resultado |
|---|---|
| `nenhum` vs `diamond` com lista negra vazia | **saída idêntica**, 2 acertos, 22 linhas |
| a checagem acima sabe falhar | `diamond` com um acerto bacteriano descarta 1, sai diferente |
| `diamond` antes vs depois (lista vazia, com bactéria, `hsp_only=YES`) | **idêntico** ao commit anterior |
| `blast` antes vs depois | **idêntico** |
| DAG, rota padrão | 350 → 350 |
| DAG, `no-nr-filter` | 346 — saem `diamond_nr` (2) e `merge_significant` (2), nada mais |
| DAG, outras 18 rotas | contagem inalterada |

`merge_significant` sair junto é correto: ela só existe para alimentar o `diamond_nr`.

## Consequências

- O pipeline passa a rodar em máquina sem espaço para o banco do NR. Essa é a única razão
  de a chave existir.
- **Sem o filtro sobram falsos positivos.** É o passo que reconhece o candidato que se
  parece mais com uma bactéria do que com um vírus. Desligá-lo não degrada um pouco: remove
  a única defesa contra o acerto espúrio. Resultado obtido assim **não é comparável** ao da
  rota padrão e não deve ser publicado como se fosse.
- O relatório **não diz** que o filtro não rodou — o campo `LNVNRE` sai `-`, igual ao modo
  `diamond`. Quem ler o resultado seis meses depois não tem como saber. Registrar a rota
  junto do resultado é responsabilidade de quem roda, e é o mesmo problema de versionamento
  do [K6](../known-issues.md).
