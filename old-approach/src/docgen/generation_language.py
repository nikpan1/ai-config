import re

from markdown_it import MarkdownIt

from docgen.storage import digest

LANGUAGE_PROFILE = {
    "id": "plain-technical-english-v1",
    "authority": "User-authorized simplified language policy; not ASD-STE100 certification",
    "rules": [
        "Use professional, plain English and direct sentences.",
        "Use one term for one concept. Define technical terms from source evidence.",
        "Prefer active voice when the source identifies the actor.",
        "Keep each sentence focused on one idea. Prefer 25 words or fewer.",
        "Preserve must, may, must not, conditions, exceptions, scope and uncertainty.",
        "Describe requirements as requirements, not as verified implementation behavior.",
        "Use headings, short paragraphs and tables to explain complex rules.",
        "Avoid decorative synonyms, jargon without definitions, and promotional language.",
        "Keep exact quotations unchanged and clearly label them as source quotations.",
        "Do not infer unknown information or remove a qualification to shorten text.",
    ],
    "exemptions": {
        "source_quotes": "Exact evidence checked separately; never rewrite",
        "code": "Preserve identifiers and code; verify surrounding explanation",
        "citation_metadata": "Preserve source IDs, hashes and locations",
        "names": "Preserve exact names; no exemption for surrounding prose",
    },
    "checks": {
        "sentence_word_limit": 35,
        "paragraph_word_limit": 150,
        "dictionary": "No normative controlled dictionary; independent model review",
        "part_of_speech": "Independent model review; no automatic certification",
    },
}


def language_contract(pipeline, state):
    inputs = pipeline.planning_inputs(state)
    knowledge = pipeline.store.get_object(inputs.knowledge_ref)
    terms = []
    for entity in knowledge["entities"]:
        if entity.get("review_status") == "ineligible":
            continue
        terms.append(
            {
                "term": entity["canonical_name"],
                "permitted_form": entity["canonical_name"],
                "definition": entity["definition"],
                "scope": entity.get("scope") or "Scope unknown; retain original source context",
                "part_of_speech": "name" if entity["kind"] == "service" else "noun",
                "authority": inputs.knowledge_ref,
                "evidence": entity["evidence"],
            }
        )
    terms.extend(pipeline.inputs(state)["generation_brief"]["terminology"])
    terms.extend(pipeline.read(state, "approved_terms_ref", []))
    blocks = {b["id"]: b for b in pipeline.store.iter_table(inputs.blocks_ref)}
    for term in terms:
        for evidence in term["evidence"]:
            if (
                evidence["block_id"] not in blocks
                or evidence["excerpt"] not in blocks[evidence["block_id"]]["content"]
            ):
                raise ValueError("Technical term has invalid source authority")
    return {
        "profile": LANGUAGE_PROFILE,
        "reference_hash": digest(LANGUAGE_PROFILE),
        "terminology": terms,
        "terminology_revision": digest(terms),
        "quote_policy": pipeline.inputs(state)["generation_brief"]["quote_policy"],
        "formal_ste_compliance": "not_claimed",
    }


def language_findings(text):
    findings = []
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    quoted = 0
    for token in tokens:
        if token.type == "blockquote_open":
            quoted += 1
        elif token.type == "blockquote_close":
            quoted -= 1
        elif token.type == "inline" and not quoted:
            prose = " ".join(
                child.content for child in token.children or [] if child.type == "text"
            )
            for sentence in re.split(r"(?<=[.!?])\s+", prose):
                words = re.findall(r"\b[\w'-]+\b", sentence)
                if len(words) > LANGUAGE_PROFILE["checks"]["sentence_word_limit"]:
                    findings.append("Long sentence: " + sentence[:180])
            if len(prose.split()) > LANGUAGE_PROFILE["checks"]["paragraph_word_limit"]:
                findings.append("Long paragraph: " + prose[:180])
    return findings
