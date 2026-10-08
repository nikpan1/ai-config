from importlib.resources import files

from docgen.storage import digest

PROMPTS = {
    "knowledge": ("extract", "verify", "entities", "claims"),
    "documentation_planning": (
        "plan_template",
        "plan_units",
        "plan_unit_synthesis",
        "plan_boundaries",
        "plan_topics",
        "plan_subdivision",
        "plan_brief",
        "plan_audit",
    ),
    "documentation_generation": ("gen_write", "gen_verify", "gen_page_review"),
}

SHARED = (
    "config.py",
    "contracts.py",
    "storage.py",
    "model.py",
    "budget.py",
    "ingestion.py",
    "signatures.py",
    "cli.py",
)
MODULES = {
    "knowledge": SHARED
    + ("batching.py", "reconciliation.py", "review.py", "validation.py", "workflow.py"),
    "documentation_planning": SHARED
    + (
        "planning_contracts.py",
        "planning_inputs.py",
        "planning_helpers.py",
        "planning.py",
        "planning_layout.py",
        "planning_validation.py",
        "planning_export.py",
        "reconciliation.py",
        "validation.py",
        "workflow.py",
    ),
}
MODULES["documentation_generation"] = MODULES["documentation_planning"] + (
    "generation.py",
    "generation_contracts.py",
    "generation_inputs.py",
    "generation_language.py",
    "generation_assets.py",
    "generation_validation.py",
    "generation_export.py",
)


def workflow_manifest(workflow):
    root = files("docgen")
    return {
        "version": "1",
        "workflow": workflow,
        "modules": {name: digest(root.joinpath(name).read_bytes()) for name in MODULES[workflow]},
        "prompts": {
            name: digest(root.joinpath("prompts", f"{name}.v1.txt").read_bytes())
            for name in PROMPTS[workflow]
        },
        "schemas": "strict-pydantic-v1",
    }


def runtime_signature(settings, workflow="knowledge"):
    return digest([settings.signature(), workflow_manifest(workflow)])
