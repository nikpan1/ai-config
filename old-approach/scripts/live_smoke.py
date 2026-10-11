from docgen.cli import run_config, runtime_signature
from docgen.config import Settings
from docgen.model import GeminiModel
from docgen.storage import Artifacts, atomic_write, encode, run_lock, write_json
from docgen.workflow import Pipeline, persistent_graph


def main():
    settings = Settings()
    store = Artifacts(settings.workspace)
    source = store.path("smoke-source/archive.md")
    text = (
        "# Synthetic archive specification\n\n"
        "This document specifies required behavior of the fictional ArchiveService. "
        "It is not evidence of implementation. "
        "All rules apply to fixture tenant A and version 1.\n\n"
        "## Terms\n\n"
        "ArchiveService is the service that stores immutable policy revisions. "
        "An archive hold is a Boolean flag on a policy revision that prevents automatic archival. "
        "An operator is a person assigned the ArchiveOperator role for fixture tenant A.\n\n"
        "## Rules\n\n"
        "ARCH-1: ArchiveService must archive eligible policy revisions once daily at 02:00 UTC. "
        "A revision is eligible when its status is approved and its archive hold is false.\n\n"
        "ARCH-2: If a revision has an archive hold, "
        "ArchiveService must skip it and record the reason. "
        "It must leave the revision unchanged.\n\n"
        "ARCH-3: An exact replay with the same logical request key "
        "must return the original result. "
        "Changed content under the same key must be rejected with ARCHIVE_KEY_CONFLICT.\n\n"
        "ARCH-4: ArchiveService must check tenant scope before reading any policy details. "
        "A request for another tenant must be rejected without returning details.\n\n"
        "ARCH-5: Only an operator may clear an archive hold, and a nonempty reason is required. "
        "Clearing a hold does not itself archive the revision.\n\n"
        "ARCH-6: A failed write must preserve the previous stored revision. "
        "The next daily run must retry the eligible revision "
        "using the original logical request key.\n"
    )
    atomic_write(source, text)
    run_id = "live-smoke-" + runtime_signature(settings)[:12]
    model = GeminiModel(settings, store, run_id)
    pipeline = Pipeline(settings, store, model)
    with run_lock(store, run_id), persistent_graph(pipeline) as graph:
        config = run_config(run_id)
        previous = graph.get_state(config)
        value = (
            None
            if previous.values
            else {
                "run_id": run_id,
                "source": str(source),
                "signature": runtime_signature(settings),
                "status": "running",
            }
        )
        graph.invoke(value, config, durability="sync")
        state = graph.get_state(config)
        result = {
            "values": state.values,
            "next": list(state.next),
            "interrupts": [item.value for item in state.interrupts],
        }
        write_json(store.path("evaluation/live-smoke.json"), result)
        print(encode(result))


if __name__ == "__main__":
    main()
