## ADDED Requirements

### Requirement: Capture thread ID from first Codex run
On the first Codex invocation in a planning cycle, the system SHALL run `codex exec --json` and parse JSONL output for the `thread_id` from the `thread.started` event. Parsing SHALL be stream-agnostic: scan all lines from both stdout and stderr for valid JSON objects with `"type": "thread.started"`. The thread ID SHALL be stored in `.claude/review/codex_thread_id`.

#### Scenario: First Codex run captures thread ID
- **WHEN** no `.claude/review/codex_thread_id` file exists and Codex is invoked
- **THEN** the system runs `codex exec --json`, scans both stdout and stderr for `thread.started` JSONL event, extracts `thread_id`, and writes it to `.claude/review/codex_thread_id`

#### Scenario: thread.started event on stdout
- **WHEN** Codex emits the `thread.started` event on stdout (typical `--json` mode)
- **THEN** the system successfully captures the `thread_id`

#### Scenario: thread.started event on stderr
- **WHEN** Codex emits the `thread.started` event on stderr (fallback/alternate mode)
- **THEN** the system successfully captures the `thread_id`

#### Scenario: thread.started event is missing from both streams
- **WHEN** neither stdout nor stderr contain a `thread.started` event
- **THEN** the system reports an error and blocks with a message to the user

### Requirement: Resume Codex session by explicit thread ID
On subsequent Codex invocations within the same planning cycle, the system SHALL read the thread ID from `.claude/review/codex_thread_id` and invoke `codex exec resume <THREAD_ID>`.

#### Scenario: Subsequent review resumes existing session
- **WHEN** `.claude/review/codex_thread_id` contains a valid thread ID
- **THEN** the system invokes `codex exec resume <THREAD_ID>` with the new prompt

#### Scenario: Resume fails, falls back to fresh session
- **WHEN** `codex exec resume <THREAD_ID>` returns a non-zero exit code
- **THEN** the system falls back to `codex exec` (fresh session), captures the new `thread_id`, and overwrites `.claude/review/codex_thread_id`

### Requirement: Never use --last or --latest
The system SHALL NOT use `--last`, `--latest`, or any relative session reference. All session references MUST use explicit thread IDs.

#### Scenario: Session reference is always explicit
- **WHEN** the system invokes Codex CLI for any purpose
- **THEN** the command line contains either no resume flag (fresh session) or `resume <THREAD_ID>` with an explicit UUID

### Requirement: Thread ID resets with planning cycle
When `approval.json` is deleted (start of a new planning cycle), the system SHALL also delete `.claude/review/codex_thread_id`. The next Codex invocation starts a fresh session.

#### Scenario: New planning cycle resets thread ID
- **WHEN** `approval.json` is deleted because Claude wrote a new plan
- **THEN** `.claude/review/codex_thread_id` is also deleted

### Requirement: Thread ID stored project-locally
The thread ID file SHALL be stored at `.claude/review/codex_thread_id` within the project directory. No global `~/` paths SHALL be used.

#### Scenario: Thread ID is in project directory
- **WHEN** the system stores or reads a Codex thread ID
- **THEN** the path is `.claude/review/codex_thread_id` relative to the project root
