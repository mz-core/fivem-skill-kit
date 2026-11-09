# FiveM Skill Kit v3.1 (neutro de framework)

Uma skill (`fivem-development/`) para qualquer agente de IA criar, corrigir e auditar resources de **FiveM/RedM** sem inventar natives e sem assumir framework. Funciona com projeto standalone, ESX, QBCore, Qbox, Ox Core ou framework próprio: ela **detecta** o que o projeto usa e manda o agente **ler o código real** em vez de chutar.

## O que mudou da v3 para a v3.1

| Tema | v3.1 |
|---|---|
| Consulta de natives | 3 fontes oficiais: docs, natives GTA V (`citizenfx/natives`) e natives CFX (`citizenfx/fivem`, `ext/native-decls`, com `apiset` client/server/shared) |
| Status do `lookup.py native` | `FOUND` (exit 0), `NOT FOUND` (1, **não é prova** de inexistência), `UNVERIFIED` (3: sem dados, fonte faltando ou só citada em texto). Menção em prosa nunca confirma. Várias definições são listadas com o API set de cada uma |
| Auditor | Resolve handlers nomeados, lado pelo manifest, SQL em várias linhas/`:format`; cada achado é `fact` (verificável em arquivos/docs) ou `heuristic` (palpite, nunca prova). `type()`/helper não contam como validação provada |
| `RegisterCommand(..., true)` | Reconhece o ACE documentado; só sugere reforço opcional (LOW) |
| Referências | Linha `> Read when:` em cada arquivo, tabela de rotas com palavras PT/EN, correções R1-R7 (`Citizen.Await` é do scheduler compartilhado, não só server) |
| Testes | selftest com fixtures de falso positivo (`clean/`), falso negativo (`regress/`), lookup com repositórios falsos, sync das 3 fontes |
| Orçamento de tokens | Metas com aviso (`validate_skill.py`), nunca bloqueiam |

Detalhes e resultados: `RELATORIO-v3.1.md`.

## Instalar

**Claude.ai (web/desktop):** envie `fivem-development.zip` na área de Skills do app.

**Claude Code, Codex, OpenCode, Copilot** (na raiz do seu projeto ou do servidor):

```bash
python install.py --project /caminho/do/projeto            # copia para todos os agentes
python install.py --project . --tools claude,codex         # só alguns
python install.py --user                                   # para sua conta (todos os projetos)
```

O Claude Code só lê `.claude/skills/` (não lê `.agents/skills/`); o instalador cuida disso.

## Atualizar

```bash
python fivem-development/scripts/sync_docs.py          # baixa docs + natives GTA + natives CFX (git; zip só para docs/natives)
python fivem-development/scripts/sync_docs.py --check  # idade dos dados (alerta após 30 dias)
python install.py --project . --update                 # nova versão da skill; mantém data/ e guarda backup fora de skills/
```

Se o agente tem shell, ele roda `lookup.py native NomeDaNative` antes de usar qualquer native. Sem os dados (ou com uma fonte faltando), o resultado é `UNVERIFIED` e a API deve ser marcada como **não verificada**. Códigos de saída: `FOUND` 0, `NOT FOUND` 1, `UNVERIFIED` 3. `sync_docs.py --check`: 2 = sem dados, 3 = dados antigos.

## Como o agente usa

1. `detect_env.py` descobre game, framework/libs, dependências desconhecidas (framework próprio aparece aqui).
2. Lê só as referências da tarefa (`SKILL.md` tem a tabela de rotas).
3. Verifica natives com `lookup.py` (FOUND / NOT FOUND / UNVERIFIED).
4. Escreve a partir de `assets/patterns` e `assets/templates`.
5. `audit_lua.py` (achados `fact` vs `heuristic`) + checklist e relatório com "testado vs não testado".

`scaffold_resource.py --name x --dest ./resources [--kind nui]` gera um resource neutro com validação no servidor.

## Verificar o kit

```bash
python fivem-development/scripts/validate_skill.py   # estrutura, frontmatter, links, neutralidade, linhas Read when, avisos de tokens
python fivem-development/scripts/selftest.py         # auditor (falso positivo/negativo), lookup, sync das 3 fontes (repositórios falsos)
```

Para provar que a skill melhora as respostas, use `fivem-development/evals/` (rode os prompts com e sem a skill, inclusive num modelo mais fraco).

## Limites (leia)

- **Lua não foi executado.** Templates e padrões não rodaram num FXServer; o auditor é heurístico (`heuristic` = palpite, `fact` = verificável em arquivos/docs). Teste num servidor de desenvolvimento seguindo `references/10-audit-checklist.md`.
- **Sync e lookup foram testados com repositórios falsos**, não com o layout real de `citizenfx/fivem-docs`, `citizenfx/natives` e `citizenfx/fivem` (GitHub estava inacessível no ambiente de teste). A busca tolera mudanças de layout; rode `sync_docs.py` uma vez e confira com `lookup.py native GetPlayerPed` e `lookup.py status`.
- Listas de funções por lado (`wrong-side-api`) vêm das páginas oficiais e podem estar incompletas; `wrong-side-native` só existe com os natives sincronizados.
- Fatos marcados **partial/unverified** em `99-sources-and-freshness.md` precisam de confirmação antes de virar regra.
- O caminho `.github/skills` do Copilot veio de documentação geral e não foi reconfirmado.
- Não há ferramenta oficial de IA da Cfx.re (llms.txt/MCP); a skill usa os repositórios públicos.

## Skill do seu projeto (opcional)

Convenções privadas (seu framework, nomes de resources, locale) ficam numa skill **separada** do seu servidor, por exemplo `meu-servidor-conventions`, que complementa esta. Assim `fivem-development` continua neutra e reutilizável.
