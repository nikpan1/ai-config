# Repository instructions for Codex

- Use English for code, identifiers, prompts, tests, logs, configuration, and software UI. Do not add code comments or explanatory docstrings; make names and control flow self-explanatory.
- Keep Python simple, readable, and cohesive. Apply SOLID and clean-code principles pragmatically: small functions, clear responsibilities, explicit dependencies, and no speculative abstractions or visual noise.
- Implement each logical pipeline stage as a LangGraph node. Use a persistent LangGraph checkpointer and a stable `thread_id` so completed stages can be inspected and resumed after a restart. Keep stages sequential where a checkpoint after each node is required.
- Request human feedback through LangGraph `interrupt()` and resume through `Command(resume=...)`; do not build a separate pause mechanism.
- Centralize logging, configuration, model setup, and file I/O in shared code. Reuse immutable clients through a small factory or singleton when useful, but never keep mutable run state in a global singleton.
- Use the Gemini API with `gemini-3.8-flash` for every model call. Reject a different `GEMINI_MODEL` value rather than silently switching models. Read secrets and configurable runtime settings from `.env`; maintain a placeholder-only `.env.example` and never commit `.env`.
- Preserve source provenance and full information coverage as described in `.ai/development-plan.md`.
