# Contributing to Rvectr

Thank you for helping. This page explains how to set up, how to send a change,
and the rules that keep the project honest. Read the [README](README.md) first
for what the project is.

## Who can contribute

Anyone can contribute.

- **Anyone:** fork the public repository (a fork is your own copy of it on
  GitHub), make your change there, and open a pull request. A pull request is a
  request to merge your change into the main project.
- **Collaborators:** people the owner has added as collaborators can push
  branches straight to this repository instead of forking.

In both cases, changes reach `main` only through a pull request. Nobody pushes
directly to `main`.

Good first changes are small: fixing a bug, adding a test, improving a
sentence in the docs. For a bigger idea (a new pipeline step, a new website
page), talk to the owner first so you do not spend time on something that
cannot be merged.

## Setup

Follow the "Quick start" in the [README](README.md). In short:

```bash
# Python (Linux or WSL 2, with uv and ffmpeg installed)
bash tools/bootstrap-linux.sh                  # CPU tools, tests and local hook
# Optional flags: --pose (CPU pose inference), --cuda --pose (NVIDIA GPU
# inference), --web (install the site packages and build the site)

# Website
npm install
```

Always run Python through `uv run --no-sync ...`. This uses the exact package
versions locked in `uv.lock`. Do not copy or activate a Windows virtual
environment inside Linux.

Real recordings and the official body-model files are private and are not in the
repository. You do not need them to work on the code. The tests use synthetic
data (data made by a program, where the right answer is known).

The bootstrap script also turns on a local Git pre-push hook. The hook checks
only the commits you are about to push, so old history does not block you. It
can still stop a push that adds a file that should not be public.

## Workflow

1. **Get the latest `main` and make a branch.** Use a descriptive name that
   starts with the kind of change: `feat/` for a new feature, `fix/` for a bug
   fix, `docs/` for documentation, and `chore/`, `refactor/` or `ci/` when they
   fit.

   ```bash
   git switch main
   git pull upstream main          # forks: add the upstream remote first (below)
   git switch -c fix/pause-at-bottom
   ```

   If you forked, link your copy to the original once with
   `git remote add upstream https://github.com/pd302423/rvectr.git`.
   Collaborators use `git pull origin main`.

2. **Make small, focused commits.** One idea per commit. Stage files by name
   (see "Project rules"), then check what is staged:

   ```bash
   git add path/to/changed_file.py
   git status
   git diff --staged
   ```

3. **Write the commit message like the existing ones.** The style is
   `type: short description`, with a lowercase, plain description in the present
   tense. The types in use are `feat`, `fix`, `docs`, `chore`, `ci` and
   `refactor`. Examples from this repository:

   ```text
   feat: add a Monte Carlo error budget for the squat-depth design
   fix: handle a pause at the bottom, short pauses and split jitter
   docs: add a pilot recording checklist
   ```

4. **Run the checks** (next section), then push your branch:

   ```bash
   git push -u origin fix/pause-at-bottom
   ```

5. **Open a pull request against `main`.** The description has a template. Say
   what changed, why, and how you checked it.

## Checks to run before a pull request

Run these yourself. Write in the pull request what you ran.

1. **Python tests.** Run them if you changed anything in `backend/`, `tools/` or
   `configs/`. They take a minute or two.

   ```bash
   uv run --no-sync pytest -q
   ```

   If you add or change Python behaviour, add a test for it. Tests use
   synthetic data.

2. **Website checks.** Run these if you changed anything in `src/`, `public/` or
   the web settings (`package.json` and similar files).

   ```bash
   npm run lint
   npm run build
   ```

   Before you change web code, read the guides in `node_modules/next/dist/docs/`.
   This version of Next.js has breaking changes, and what you remember from older
   versions may be wrong.

3. **Publish check.** This looks for files that must never be published: model
   files, recordings and other media, generated results, and text that looks
   like a secret key.

   ```bash
   uv run --no-sync python tools/check_publish.py
   ```

   Fix any findings that your changes introduce. By default the check compares
   your branch with the common base of `upstream/main`, `origin/main` or local
   `main`, and it also inspects staged and untracked files. Fetch `main` first so
   it can find that base. Older files in the Git history are not your concern:
   the owner keeps a private audit of them.

4. **Documentation changes.** Check that every command and file path you wrote
   really exists, and that nothing in your text claims more than has been shown.

## Project rules

These rules protect the research and the people in it.

**Keep private data out of the repository.** Never commit:

- official SMPL model files (body-model data with its own licence),
- raw recordings and calibration records,
- videos or photos of people,
- generated body meshes,
- `.env.local` (it holds the private locations of data and models).

Use `.env.example` as the format and keep your real settings in `.env.local`.
Do not put personal names, email addresses or paths from your own computer into
files either. If a `video/` folder exists on your machine, it is a separate
project (a Remotion video project) and is not part of the app. Leave it alone.

**Stage files by name.** Never use `git add -A` or `git add .`, and avoid
`git commit -a`. The working folder on a computer can hold personal recordings
and other private files, and these commands would stage them. Use
`git add path/to/file`, then look at `git status`.

**Keep missing data missing.** If a measurement is absent (a hip was not found, a
frame was dropped, a squat was only partly seen), leave it missing or mark it
"unclear". Do not fill gaps, guess values or replace them with averages. Keep the
original timestamps of the data. Failed and blocked runs keep their run numbers.

**Never invent data.** No hand-typed measurements and no made-up numbers in code,
docs or the website. A number must come from a script that anyone can run again.

**Make no accuracy claim without real validation.** Everything checked so far
uses synthetic data. A passing environment check, a passing test, or a 3D model
that looks right is not an accuracy result. An accuracy claim needs real
recordings and an independent reference measurement.

**Label simulated numbers as simulated.** Anywhere a number from the error
budget or another simulation appears, say next to it that it is a simulation
prediction, not a measurement.

**Be careful with the older scripts.** Many scripts at the top of `backend/` are
old and have known defects. Read [backend/README.md](backend/README.md) and
[critical_analysis.md](critical_analysis.md) before running or editing them.

**Mind the licence.** Contributions are shared under the same terms as the rest
of the project: research, education and non-profit use only (see
[LICENSE](LICENSE)). If you add a library, model or dataset, say in your pull
request what licence it has.

**Write plainly.** In docs and on the website, use short sentences, explain a
technical term the first time it appears, and do not use emojis.

## Using AI coding assistants

You may use any AI coding assistant, such as Claude, Codex or Astra. Some rules:

- Tell the assistant to read [AGENTS.md](AGENTS.md) and this file before it
  starts. (`CLAUDE.md` just points to `AGENTS.md`.)
- **You are responsible for everything it writes.** Read every change, run the
  checks yourself, and be able to explain the change in your own words.
- Make sure it follows the project rules above. In particular it must not invent
  data or accuracy numbers, must not stage with `git add -A` or `git add .`, and
  must not push to `main`, rewrite history or force-push.
- The section of `AGENTS.md` called "Luna delegation policy" is the owner's
  personal preference for the owner's own sessions. It does not restrict you.
  Use your own checkout and local settings. The rest (the Next.js warning, the
  runtime notes and the data rules) does apply.
- Competition rules may require that the use of AI is disclosed. If an AI
  assistant wrote a substantial part of your pull request, say so in the "AI
  assistance" part of the description: which tool, and for what.

## Reviews and merges

The owner reviews every pull request and merges it. You do not merge your own.

- Keep pull requests small and about one idea. They are reviewed faster, and a
  small mistake is easier to find.
- Expect questions or requests for changes. Answer them and push more commits to
  the same branch. The pull request updates by itself.
- A pull request may be turned down if it breaks a project rule above, even when
  the code works. This is usually about data or honesty of claims, not about
  your skill.
