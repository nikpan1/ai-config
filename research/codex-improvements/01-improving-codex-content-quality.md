# Improving Content Quality with Codex

> Research current as of 7 October 2026. Scope: practical repository configuration
> for Codex/ChatGPT, not building a custom API agent.

## Conclusion

The largest quality improvement does not come from a longer “superprompt.” It comes
from a light, layered setup: a concise AGENTS.md for repository-wide rules, narrow
skills for repeatable workflows, and measurable verification of the finished result.
This keeps irrelevant context out while giving Codex the information it needs when it
needs it.

This repository now uses that structure:

    AGENTS.md
    .codex/skills/content-research/SKILL.md
    Research/
      01-improving-codex-content-quality.md
      02-sources.md

## 1. Design context, not only prompts

OpenAI's Codex guide identifies autonomy, exploration, tool use, and output quality
as critical instruction areas; an agent should deliver a working result rather than
only a plan ([Codex Prompting Guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)).

A good request supplies only the details that change decisions:

- outcome: what should be produced and for whom;
- boundaries: what is outside scope and when a question is required;
- acceptance criteria: how completion can be recognized;
- quality evidence: relevant tests, rendering, sources, or review.

For example: “Compare X and Y for the product team. Use vendor documentation and
data no older than one year; recommend an option with reasoning, cite technical
claims, and identify evidence gaps.”

Do not require the agent to read all documentation before a small change, nor attach
a rigid procedure to every prompt. Excess instructions consume context, may conflict,
and slow the work. It is better to indicate when a specific document is needed
([Rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)).

## 2. AGENTS.md: a shared quality contract

AGENTS.md is the right place for durable repository rules. Codex collects
instructions from the global level through the current directory; instructions from
deeper directories are applied later
([Codex Prompting Guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)).

| Include | Avoid or move elsewhere |
| --- | --- |
| result and verification standards | generic advice the model already knows |
| local test commands and safety limits | a workflow for only one document type |
| source, language, and response rules | a full repository map required for every edit |
| the condition for using a plan | a lengthy plan template in the base file |

The current [AGENTS.md](../AGENTS.md) deliberately remains short. It establishes
quality, verification, citations, language defaults, and when to plan without
forcing one sequence for every task.

## 3. Skills: only for narrow, repeatable workflows

A skill is a directory with a SKILL.md instruction file and optional resources.
During discovery, Codex sees its name and description, so that description must
accurately state both the action and when to use it
([Skills documentation](https://developers.openai.com/api/docs/guides/tools-skills)).

Add a skill when a workflow repeats, has its own quality criterion, or needs
reference material. Do not add one merely to hold another set of generic advice.
Short descriptions and progressive disclosure—reading supporting material only when
needed—improve selection accuracy and limit context overhead
([Rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)).

This repository includes one focused skill, content-research. It handles source-backed
research and Markdown documents; it is intentionally not a catch-all writing skill.

Possible future skills, but only once the workflow genuinely repeats:

- docx-quality — when Word documents require layout verification;
- pdf-quality — when PDFs must be rendered and visually assessed;
- api-reference — when one API is used often enough for maintained local rules and
  examples to be valuable.

Each skill should have a positive invocation test and a negative test that detects
over-broad matching. OpenAI recommends measuring outcome, process, style, and
efficiency separately rather than relying on one pass/fail result
([Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)).

## 4. Research: sources are part of the deliverable

Good content should not merely sound convincing. Every material external fact needs
a link to the page that supports it; prefer the source owner for a product or
standard. Label interpretation as an inference or recommendation rather than
presenting it as a cited fact.

The added skill enforces those distinctions and requires checking that links lead to
the supporting page, not search results. This matters especially for API
specifications, pricing, policies, market data, and product information.

## 5. Plan only work that is complex enough

For a large feature, refactor, or multi-hour task, a living plan is useful: it
records scope, decisions, verification points, and enables resumption. OpenAI
describes the PLANS.md or ExecPlan pattern for taking complex work from design to
implementation ([Using PLANS.md for multi-hour problem solving](https://developers.openai.com/cookbook/articles/codex_exec_plans)).
Do not require it for simple fixes.

## Request template

    Goal: [the result and intended audience].
    Scope: [included work] / out of scope: [excluded work].
    Definition of done: [observable conditions].
    Quality evidence: [tests, render, sources, review].
    Constraints: [technology, style, deadline, security].

Fill only the fields that genuinely constrain a decision. For research, add:
“Use content-research.”

## Repository-owner checklist

- Does the base instruction describe local rather than universal rules?
- Is every rule still needed for current models?
- Does a skill have a narrow trigger and repeatable value?
- Is the definition of done observable?
- Does every current research claim have a source or a stated limitation?

See [02-sources.md](02-sources.md) for the source register.

