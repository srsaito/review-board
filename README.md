# review-board

A multi-model code review tool that sends your documents to multiple LLMs (ChatGPT, Gemini, and optionally Claude) for independent review, then merges the results into a structured, actionable state file.

Each reviewer scores the artifact on correctness, completeness, testability, risk, and maintainability, and produces a list of grounded issues. A moderator (Claude Code) then merges the reviews into a single state file that classifies findings as agreements, must-fix items, needs-verification items, or disputes with tie-break questions.

## How It Works

```
                    ┌─────────────┐
  artifact.md ─────►│             │
                    │  LiteLLM    │──► ChatGPT review JSON
  reference docs ──►│  Proxy      │──► Gemini  review JSON
                    │             │──► Claude  review JSON (optional)
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Claude     │
                    │  Moderator  │──► state_turn1.json
                    └─────────────┘
```

1. **Reviewers** independently score and critique the artifact against reference documents
2. **Moderator** (Claude Code) merges findings into a structured state file:
   - **Agreements** -- both reviewers flagged the same issue
   - **Must-fix** -- single-reviewer blocker/major with strong evidence
   - **Needs verification** -- single-reviewer finding lacking evidence or a gate
   - **Disputes** -- reviewers disagree; includes options, pros/cons, and a tie-break question
3. **Rebuttal turns** (optional) let reviewers refine positions on open disputes

## Prerequisites

- Python 3.10+
- API keys for the models you want to use (OpenAI, Google, Anthropic)
- [LiteLLM](https://github.com/BerriAI/litellm) proxy running locally
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI (for moderation and optional Claude reviewer)

## Installation

```bash
git clone https://github.com/srsaito/review-board.git
cd review-board
uv tool install -e .
```

This installs two CLI commands:

| Command | Description |
|---------|-------------|
| `review-board` | Run multi-model review on an artifact |
| `validate-state` | Validate a moderated state JSON file against the schema |

## Setup

### 1. Install the Claude Code skill

The `/review` skill lets you run the full pipeline (reviewers + moderation + validation) from inside Claude Code.

**Option A: All projects (user-level)**

```bash
mkdir -p ~/.claude/skills/review
cp skill/SKILL.md ~/.claude/skills/review/SKILL.md
```

Makes `/review` available in every project on this machine.

**Option B: Single project (project-level)**

```bash
mkdir -p <project>/.claude/skills/review
cp skill/SKILL.md <project>/.claude/skills/review/SKILL.md
```

Makes `/review` available only in that project. Useful if you want to customize defaults (e.g., hardcode `--reference-docs` for that project).

If both exist, the project-level skill overrides the user-level one.

### 2. Configure API keys

Set environment variables for the providers you plan to use:

```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
```

### 2. Configure and start the LiteLLM proxy

The proxy config is user-level (shared across projects that use the same LiteLLM
instance, e.g. review-board + voice-chatbot). Copy the example config to
`~/.config/litellm/` and customize it:

```bash
mkdir -p ~/.config/litellm
cp config/litellm-example.yaml ~/.config/litellm/config.yaml
```

Edit `~/.config/litellm/config.yaml` to set your preferred models. The defaults are:

```yaml
model_list:
  - model_name: review_chatgpt
    litellm_params:
      model: openai/gpt-4.1

  - model_name: review_gemini
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY
      api_base: https://generativelanguage.googleapis.com/v1beta
```

Start the proxy:

```bash
litellm --config ~/.config/litellm/config.yaml
```

The proxy runs on `http://127.0.0.1:4000` by default.

## Usage

### Running a review

```bash
review-board <artifact> \
  --reference-docs <doc1>,<doc2>
```

**Example:**

```bash
review-board docs/plan/EP-04-tasks.md \
  --reference-docs docs/architecture/SYSTEM_DESIGN.md
```

The command outputs a JSON result to stdout with the session directory and paths to reviewer outputs:

```json
{
  "session_dir": "docs/reviews/EP-04-tasks-20260308-143022-a1b2c3d4",
  "status": "ok",
  "outputs": {
    "chatgpt": "docs/reviews/.../turn1_chatgpt.json",
    "gemini": "docs/reviews/.../turn1_gemini.json"
  }
}
```

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--reference-docs` | *(required)* | Comma-separated paths to reference documents |
| `--api-base` | `http://127.0.0.1:4000` | LiteLLM proxy URL |
| `--out-base` | `docs/reviews` | Output directory for review sessions |
| `--chatgpt-model` | `review_chatgpt` | Model alias for ChatGPT reviewer |
| `--gemini-model` | `review_gemini` | Model alias for Gemini reviewer |
| `--temperature` | `0.0` | Sampling temperature |
| `--max-tokens` | `8192` | Max output tokens per reviewer |
| `--claude-reviewer` | *(off)* | Enable Claude Code CLI as a third reviewer |
| `--claude-model` | `sonnet` | Claude model (`sonnet`, `opus`, `haiku`) |

### Moderation (via Claude Code)

After `review-board` produces reviewer outputs, Claude Code acts as the moderator. If you use the bundled `/review` skill inside Claude Code, this happens automatically:

```
/review docs/plan/EP-04-tasks.md --reference-docs docs/architecture/SYSTEM_DESIGN.md
```

This runs the full pipeline: reviewers, moderation into `state_turn1.json`, and validation.

To add rebuttal turns (reviewers respond to disputes):

```
/review docs/plan/EP-04-tasks.md --reference-docs docs/architecture/SYSTEM_DESIGN.md 3
```

The trailing number sets the max turns (1 = initial critique only, 2 = critique + one rebuttal, etc.).

### Validating state files

```bash
validate-state docs/reviews/session-dir/state_turn1.json
```

Prints `OK` on success, or exits with code 1 and an error message on failure.

## Session directory structure

Each review run creates a timestamped session directory:

```
docs/reviews/EP-04-tasks-20260308-143022-a1b2c3d4/
├── run.json                  # Run metadata (models, params, hashes)
├── artifact_snapshot.md      # Frozen copy of the artifact
├── reference_snapshot.md     # Frozen copy of reference docs
├── turn1_chatgpt_raw.txt     # Raw ChatGPT output
├── turn1_chatgpt.json        # Validated ChatGPT review
├── turn1_gemini_raw.txt      # Raw Gemini output
├── turn1_gemini.json         # Validated Gemini review
└── state_turn1.json          # Moderated state (after moderation)
```

Review sessions are ephemeral development artifacts. Consider adding `docs/reviews/*/` to your project's `.gitignore`.

## License

MIT
