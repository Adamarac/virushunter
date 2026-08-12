# 0002 — Base de trabalho e fork

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

O repositório de origem é `xutaodeng/virushunter` — público, sem licença declarada,
branch padrão `master`, último push em 2020-07-12.

No momento desta decisão existia **um** fork: `amphybio/virushunter`, criado em
2025-01-13 pelo grupo AMPhyBio, com quatro commits além do upstream:

```
8fb8772  readseeds2: adjust path
8583445  script filter database
4236462  nr_virus: use filtered taxonomy databases
5c5d1d4  gitignore generated files
```

Esses commits comentam o prefixo `wd='/mnt'+wd` em `readseeds2.py` e adicionam
`print 'the end'` — indícios de uma tentativa de executar o pipeline fora do cluster
original — além de ajustes na construção dos bancos de taxonomia.

Existe também `Adamarac/virushunter-nextflow` (privado, 2025-06-30). Seu conteúdo é
apenas o tutorial "Hello world" do Nextflow (processos `split` / `convert_to_upper`),
sem nenhum código do VirusHunter. Não é material aproveitável, mas registra que Nextflow
já foi cogitado como ferramenta de workflow.

## Alternativas consideradas

**Trabalhar em `amphybio/virushunter`.** Reaproveitaria os quatro commits e manteria o
trabalho no espaço do grupo. Descartada: o trabalho de 2025 é exploratório e trazê-lo
misturaria uma base experimental com uma refatoração planejada.

**Fork em `AlanCpic`.** Essa conta possui o escopo `workflow` no token, necessário para
publicar GitHub Actions. Descartada por ora; o escopo pode ser adicionado a `Adamarac`
com `gh auth refresh -s workflow` quando houver necessidade.

**Fork em `Adamarac`.** Base limpa a partir do estado de 2020, separada tanto do
upstream quanto do trabalho experimental do grupo.

## Decisão

1. Usar `Adamarac/virushunter` como base, forkado a partir de `xutaodeng/virushunter`.
2. Partir do estado de 2020. **Ignorar** os quatro commits de `amphybio` e não
   configurar aquele repositório como remote.
3. Manter o clone original de 2020 intocado como referência, e trabalhar num clone
   separado do fork.
4. Manter `upstream` configurado apontando para `xutaodeng/virushunter`.

## Consequências

- O ajuste de path do `readseeds2.py` e a filtragem de taxonomia do `nr_virus3.py`
  precisarão ser refeitos se vierem a ser necessários. O material permanece acessível em
  `amphybio/virushunter` caso a decisão seja revista.
- O fork não tem licença, porque o upstream não tem. **Isso limita a redistribuição.**
  Resolver exige contato com o autor original (Xutao Deng, xutaodeng@gmail.com). Fica
  registrado como pendência, não resolvido por esta ADR.
- O token de `Adamarac` não possui o escopo `workflow`; publicar GitHub Actions exigirá
  `gh auth refresh -s workflow`.
- Credenciais em texto claro presentes no upstream (`virus_hunter.py:1950` e comentários
  nas linhas 146–160) foram herdadas pelo fork e **devem ser tratadas como
  comprometidas**, independentemente de remoção futura: já estão públicas desde 2020.
