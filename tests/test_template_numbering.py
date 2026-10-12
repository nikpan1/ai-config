import pytest

from docgen_graph.authoring.template import document_title, heading_tree, number_generated_headings


def test_tree_ignores_fences_and_preserves_ids_on_title_changes():
    first = heading_tree("## 3. Behavior\n```md\n### Fake\n```\n### 3.1 First\n")
    second = heading_tree("## 3. Rules\n\nA paragraph\n### 3.1 Renamed\n")
    assert [item["section_id"] for item in first] == [item["section_id"] for item in second]
    assert len(first) == 2


def test_generated_numbering_and_nested_sections():
    text = "### 3.1 First\n### 3.2 Second\n#### Detail\n### Additional"
    result = number_generated_headings(text, "3", ["3.1 First", "3.2 Second"])
    assert "#### 3.2.1 Detail" in result
    assert "### 3.3 Additional" in result
    assert number_generated_headings("### Plain", "", []) == "### Plain"


def test_conflicting_fixed_numbers_rejected():
    with pytest.raises(ValueError, match="conflicts"):
        heading_tree("## 3. Rules\n### 4.1 Invalid")
    with pytest.raises(ValueError, match="Duplicate"):
        heading_tree("## 3. Rules\n### 3.1 One\n### 3.1 Two")


def test_title_prefers_template_without_banning_product_plans():
    assert document_title("Documentation Plan", "# Product Guide", "") == "Product Guide"
    assert document_title("Plan for documentation", "## Rules", "") == "Product documentation"
    assert document_title("Disaster Recovery Plan", "## Rules", "") == "Disaster Recovery Plan"
    assert document_title("Pricing Plan", "## Rules", "") == "Pricing Plan"
