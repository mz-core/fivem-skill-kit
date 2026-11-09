# Relatório v3.1 — FiveM Skill (neutra de framework)

Versão separada da v3. Nada foi instalado, publicado ou substituído.

## 1. Alterações

**Natives (N1–N3)**
- Três fontes oficiais: docs (`citizenfx/fivem-docs`), natives GTA V (`citizenfx/natives`) e natives CFX (`citizenfx/fivem`, só `ext/native-decls`, via clone esparso; o zip do repositório inteiro não é usado por ser enorme).
- `lookup.py native`: `FOUND` (0) / `NOT FOUND` (1) / `UNVERIFIED` (3). `NOT FOUND` só aparece com as duas fontes de natives sincronizadas e sempre diz "não é prova". Fonte faltando ou sem dados = `UNVERIFIED`.
- Mostra API set (client/server/shared), `ns` e fonte; várias definições são listadas, e conflito de API set é avisado.
- Menção em texto nunca confirma: definição = nome do arquivo, título, declaração C em bloco de código, ou linha `// 0xHASH`.
- Helper compartilhado `_natives.py` (único arquivo novo em scripts; usado por lookup e auditor).

**Auditor (A1–A8)**
- Handlers nomeados e inline; lado (client/server) pelo manifest, depois por prefixo `sv_`/`cl_`, senão "desconhecido" (reportado).
- Cada achado: `fact` (verificável em arquivos/docs) ou `heuristic` (palpite). Severidade = prioridade de revisão.
- A4: `type()`/`tonumber()` ou função validadora **não** provam validação; viram heurística com a limitação escrita. Sem nenhum desses sinais: LOW, ou MEDIUM se o handler chama operação sensível.
- A6: `RegisterCommand(..., true)` continua reconhecido como ACE documentado; só sugere reforço opcional (LOW). Comando sem restrição nem checagem: MEDIUM.
- SQL por análise de cadeia de strings (várias linhas, `:format`/`string.format`; concatenação só de literais não é marcada).
- `wrong-side-api` (lista documentada, avisa que pode estar incompleta) e `wrong-side-native` (só com natives sincronizados).
- Saída compacta: `SUMMARY`, caminhos relativos, máx. 15 achados (`--all` mostra tudo), `--json` com `summary/findings/notes`.

**Referências (R1–R7, D1–D3)**
- `dependency` de runtime, `resmon`/`profiler`, texto de `RegisterCommand`, seção "shared vs side-specific" (**`Citizen.Await` e `Citizen.Wait` são do scheduler compartilhado**, não exclusivos do server), assinatura de `AddStateBagChangeHandler`, net ID/entity handle, `99` reescrito (verified/partial/unverified).
- Cada referência começa com `> Read when:`. `SKILL.md` tem "Minimum path" de 6 passos e tabela de rotas com palavras PT/EN. Recomendações opcionais estão marcadas como "recommended", não como exigência da plataforma.

**Testes (T1–T5)**: ver seção 2. Evals 10 → 14. Orçamento de tokens só avisa.

## 2. Testes executados

| Verificação | Resultado |
|---|---|
| `selftest.py` | **96 passed, 0 failed** |
| `validate_skill.py` | OK, 0 erros, 0 avisos (frontmatter, links, rotas, neutralidade, "Read when", evals) |
| Tokens (estimativa chars/4) | SKILL.md ≈1260, referências ≈11300 (metas 2000 / 1600 por arquivo / 12000; só avisam) |
| Instalador | `--project`, `--update` (mantém `data/`, backup fora de `skills/`), `--mode symlink`; cópia instalada valida |
| Scaffold `basic` e `nui` | 0 HIGH/MEDIUM no auditor |
| `detect_env` | não assume framework; acusa `lua54 'yes'` e NUI sem strict mode |

**Falso negativo** (`bad_resource` + `regress/`): 17 códigos semeados detectados; handler nomeado, lado só pelo manifest e SQL multilinha/`:format` detectados.
**Falso positivo** (`clean/`, 6 fixtures): helper de validação, `cb` repassado, comando com ACE, nomes `sv_`/`cl_`, palavras-chave dentro de comentários e strings: 0 HIGH, 0 MEDIUM.
**Lookup** (repositórios falsos): FOUND com API set, por hash, por UPPER_SNAKE; duas definições; menção só em prosa não vira FOUND; fonte CFX ausente = UNVERIFIED; sugestão de typo; sync por git e zip; falha preserva dados antigos.

### Defeitos reais que os próprios testes acharam e foram corrigidos
1. `ExecuteCommand(...)` dentro de string `[[ ]]` virava HIGH (busca era no texto com strings).
2. `qty/quantity/count/total` gerava MEDIUM `client-controlled-value`: removidos; ficam `price/cost/amount/money/reward/...`.
3. `("SELECT ... '%s'"):format(x)` não era detectado (faltava aceitar o `)`).
4. Uma frase "See also NOME() ..." em página de native era aceita como declaração C e dava FOUND: agora em `.md` só vale dentro de bloco de código, com prefixo parecido com tipo e linha terminando como declaração.
5. `math.tointeger` passou a contar como sinal básico (continua heurístico).

## 3. Limites conhecidos
- Lua não foi executado; sem FXServer. Auditor é heurístico.
- GitHub estava inacessível aqui: `sync_docs.py` (clone esparso de `ext/native-decls`) e o layout real dos três repositórios **não foram testados na rede real**. O lookup é agnóstico de layout, mas rode `sync_docs.py` e `lookup.py status` uma vez na sua máquina.
- Listas client-only/server-only vêm das páginas oficiais e podem estar incompletas.
- Helper de validação em outro arquivo ainda pode gerar LOW/MEDIUM falso (declarado na mensagem).
- Fatos `partial/unverified` seguem listados em `references/99-sources-and-freshness.md`.

## 4. Próximo passo (seu)
Testar com e sem a skill em modelo forte e pequeno, usando `evals/evals.json` (14 prompts). Nenhuma funcionalidade nova foi iniciada.
