# Git Rules: Route Planner

Simple rules for a small, fast project. The goal is a clean history a reviewer can read.

---

## 1. Branches

| Branch | Use |
|---|---|
| `main` | Always working. What gets deployed and reviewed |
| `feature/<yyyy-mm-dd>/<name>` | New feature, for example `feature/2026-10-23/routing` |
| `fix/<yyyy-mm-dd>/<name>` | Bug fix, for example `fix/2026-10-23/eta-timezone` |
| `docs/<yyyy-mm-dd>/<name>` | Documentation only |
| `chore/<yyyy-mm-dd>/<name>` | Setup, config, deployment |

Rules:
- Keep branches short-lived: merge the same day.
- Never commit broken code to `main`. Run the tests first.
- Working alone on a tight timeline, committing straight to `main` is acceptable for small changes, as long as it stays working.

---

## 2. Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>
```

| Type | When |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `test` | Adding or changing tests |
| `refactor` | Code change with no behavior change |
| `docs` | Documentation |
| `chore` | Setup, dependencies, config |
| `style` | Formatting only |
| `perf` | Performance improvement |

**Scopes:** `api`, `routing`, `weather`, `risk`, `ranking`, `heatmap`, `ui`, `map`, `deploy`, `docs`.

**Examples:**
```
chore: set up Django + DRF and React + MUI skeleton
feat(routing): fetch 3 truck routes from TomTom
feat(routing): add via-point fallback when fewer than 3 routes
feat(weather): batch Open-Meteo requests for checkpoints
feat(risk): classify wind, rain and snow with load rules
test(risk): cover threshold edges and load limits
feat(ui): add route cards with recommended badge
fix(weather): use end-of-hour value for ETA lookup
docs: add PRD and architecture
```

**Summary line rules:**
- Present tense, lower case after the colon: "add", not "Added"
- 72 characters or less
- No period at the end
- Says *what* changed; add a body line for *why* if it isn't obvious

---

## 3. When to commit

- One commit per finished, working step (roughly one task in task.md).
- Commit tests with the code they test, or right after.
- Don't bundle unrelated changes in one commit.
- Commit at least every hour; push at least at the end of each block.

---

## 4. Never commit

- `.env` or any API key, password or secret
- `venv/`, `node_modules/`
- `db.sqlite3`
- `__pycache__/`, `*.pyc`
- `dist/`, build output
- Editor and OS files (`.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db`)

Commit `.env.example` with variable names and no real values:
```
TOMTOM_API_KEY=
DJANGO_SECRET_KEY=
DEBUG=True
```

**If a secret is committed by mistake:** revoke the key at the provider straight away and create a new one. Removing it in a later commit is not enough, because it stays in the history.

---

## 5. Required files

`.gitignore`:
```
venv/
__pycache__/
*.pyc
.env
db.sqlite3
node_modules/
dist/
.vscode/
.idea/
.DS_Store
Thumbs.db
```

`.gitattributes` (keeps line endings consistent on Windows):
```
* text=auto
```

---

## 6. Before every push

- [ ] Backend tests pass: `python manage.py test`
- [ ] Frontend builds: `npm run build`
- [ ] No secrets in `git diff --staged`
- [ ] Commit messages follow section 2

---

## 7. Merging

```bash
git checkout main
git merge --no-ff feature/2026-10-23/routing -m "feat(routing): merge truck routing"
git branch -d feature/2026-10-23/routing
git push
```

Use `--no-ff` so each feature shows up as one clear unit in the history.

---

## 8. Release

When submitting:
```bash
git tag -a v1.0 -m "Submission version"
git push origin v1.0
```

Don't push changes to `main` after submitting unless asked. If you must, tag them `v1.1` and mention it.

---

## 9. First push to GitHub

Create an **empty** `route-planner` repo on GitHub (no README, no .gitignore), then:
```bash
git remote add origin https://github.com/<your-username>/route-planner.git
git branch -M main
git push -u origin main
```
