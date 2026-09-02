# AI Tool Use

- **Where and why:** I used Claude Fable and GPT-5.6 Sol xhigh as supervised completion and review assistants. I added most files and wrote most of their content myself from my own snippets and established mental patterns; AI completed portions under specific direction or reviewed them for inconsistencies. I delegated the utilities under `scripts/` and the experimental security-review skills and hooks more fully. I also used AI to turn hand-maintained assessment notes into first drafts of the final reports, which I finalized myself. Drawing on prior CI/CD, security automation, and FastAPI experience, I independently reviewed the application and made the architecture, risk, and prioritization decisions.

- **What it got right:** AI was most reliable at bounded completions: CodeQL scaffolding, implementing the shared Semgrep gate script, handling utility scripts, and organizing my notes into report drafts. Even these outputs required review and revision. Overall, AI did not save me time.

- **What it got wrong or missed:** Fable initially split image scanning across several workflows instead of following my direction to use a parameterized reusable workflow. More significantly, after a long discussion about nondeterministic broken-access-control detection, I requested a broad, harness-agnostic reviewer and warned it not to overfit this assessment. Fable assured me its prompts were generic, but mapped its reviewer taxonomy, prompts, and evaluations directly to the seeded findings—producing expensive agentic regression tests instead of a discovery tool. It ran the most expensive whole-tree mode without a cost warning and continued launching verifiers after I questioned its resource usage. This first pass consumed about 1.9 million tokens, cost $50.44, and exhausted the session limit within minutes.

  GPT-5.6 Sol xhigh also failed repeatedly while drafting this note. When instructed to include these screenshots as a separate example of AI failure, it kept reading and summarizing them instead. I had to repeat the instruction four times.

  **Evidence of the GPT-5.6 drafting failures:**

  [![Sol draft failed instruction](./assets/sol-draft-failure.png)](./assets/sol-draft-failure.png)

  [![Third failed instruction](./assets/sol-fail-3rd.png)](./assets/sol-fail-3rd.png)

  [![Fourth failed instruction](./assets/sol-fail-4th.png)](./assets/sol-fail-4th.png)

  **Evidence from Fable's failed first pass:**

  [![Request for a broad reviewer following the broken access-control discussion](./assets/request.png)](./assets/request.png)

  [![Explicit check that the skill was not overfitting the seeded findings](./assets/check-in.png)](./assets/check-in.png)

  [![Post-run acknowledgement of the design, execution, and cost failures](./assets/result.png)](./assets/result.png)

- **How I verified it:** I reviewed the FastAPI code and triaged each SCA finding for reachability myself. I manually inspected AI completions against my intended architecture and source notes, ran targeted checks, and finalized all written deliverables. After my review, I used AI subagents as a second pass; they found nothing I had missed. I did not treat generated output or confident explanations as evidence.

- **Effect on decisions:** AI did not change my CI design, custom-rule direction, vulnerability prioritization, or triage decisions. It completed portions of files and implementations I had already written and turned my existing notes into report drafts. Its failures reinforced the need for narrow tasks, explicit acceptance criteria, cost controls, and human review.
