# AI Tool Use

Drawing on my prior CI/CD, security automation, FastAPI, and general coding experience, I independently reviewed the application and made the architecture, risk, and prioritization decisions. I added most files and wrote most of their content myself from my own snippets and established mental patterns.

I used Claude Fable, GPT-5.6 Sol xhigh, and GitHub Copilot as supervised completion and review assistants. AI completed portions under specific direction or reviewed them for inconsistencies. I allowed the AI to fully generate portions of the work, but still with my oversight, design, and direction:

- utilities under `scripts/`
- agent skill `.agents/skills/sec-review`
- access control test `tests/test_authz_invariant.py`
- Most first drafts of documentation from my structured notes

AI did not change my CI design, custom-rule direction, vulnerability prioritization, or triage decisions. It completed portions of files and implementations I had already written and turned my existing notes into report drafts. Its failures reinforced the need for narrow tasks, explicit acceptance criteria, cost controls, and human review.

_**What it got right, what it got wrong...**_

As a heavy adopter of agentic AI, I would not measure AI in a right-or-wrong binary. Just like you would not say a hammer is right or wrong, AI is a tool and a force multiplier. It rarely gets something right on its own. Its output quality depends heavily on the clarity of the instructions, the context provided (the quality of the codebase is just as much an input as your prompt), and how the human wielded it.

AI was most reliable at bounded completions: CodeQL scaffolding, implementing the shared Semgrep gate script, handling utility scripts, and organizing my notes into formatted report drafts.

But never on the first pass. Here are some examples...

- Fable initially split image building, scanning, and releasing across several disjointed workflows. I had to course correct it to use a parameterized reusable workflow to simplify the implementation.
- Fable, after a long planning discussion to create a harness-agnostic security reviewer skill, explored the codebase and found my triage findings. These findings must have been a tempting shortest path, or they influenced the generations so much that Fable abandoned the entire plan and mapped its reviewer taxonomy, prompts, and evaluations directly to the seeded triage findings. The result was essentially a very expensive agentic regression test instead of a discovery and review tool. It ran the most expensive whole-tree mode without a cost warning and continued launching verifiers after I questioned its resource usage and loss of direction, assuring me none of that was true and things were on course. This first pass consumed about 1.9 million tokens, cost $50.44, and exhausted the session limit within minutes. Both models really struggled with converting the triage notes into the write-up. They consistently and independently kept combining findings into a single row instead of listing each one granularly and failed to follow explicit instructions for structuring the report. They kept conflating the requirements and over-editorializing.

  **Evidence from Fable's failed first pass:**

  [![Request for a broad reviewer following the broken access-control discussion](./assets/request.png)](./assets/request.png)

  [![Explicit check that the skill was not overfitting the seeded findings](./assets/check-in.png)](./assets/check-in.png)

  [![Post-run acknowledgement of the design, execution, and cost failures](./assets/result.png)](./assets/result.png)

  GPT-5.6 Sol xhigh also failed repeatedly while drafting this note. When instructed to include these screenshots as a separate example of AI failure, it kept reading and summarizing them instead. I had to repeat the instruction four times.

  **Evidence of the GPT-5.6 drafting failures:**

  [![Sol draft failed instruction](./assets/sol-draft-failure.png)](./assets/sol-draft-failure.png)

  [![Third failed instruction](./assets/sol-fail-3rd.png)](./assets/sol-fail-3rd.png)

  [![Fourth failed instruction](./assets/sol-fail-4th.png)](./assets/sol-fail-4th.png)




In my experience, AI does not necessarily save time, but it can help conserve mental energy and get through repetitive or structured tasks more efficiently. Because it is probabilistic, it rarely outputs something as desired and can require many passes to get close to right, which can take more time than usual, especially when using larger models.
