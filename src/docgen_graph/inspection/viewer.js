"use strict";
const D = JSON.parse(
  new TextDecoder().decode(
    Uint8Array.from(atob(document.getElementById("dataset").textContent), (c) =>
      c.charCodeAt(0),
    ),
  ),
);
const $ = (id) => document.getElementById(id);
const json = (value) => JSON.stringify(value, null, 2);
const compact = (value) =>
  typeof value === "string" ? value : JSON.stringify(value);
const state = {
  view: "graph",
  graph: "current",
  query: "",
  table: "nodes",
  filters: {},
  selected: null,
  hops: 0,
  graphMode: "topology",
  neighborLimit: 8,
  page: 0,
};
let topologyView = null;
const asRecords = (value) =>
  Array.isArray(value)
    ? value.filter(
        (item) => item && typeof item === "object" && !Array.isArray(item),
      )
    : [];
const palette = [
  "#70dab3",
  "#79aeea",
  "#edbc79",
  "#ca96dd",
  "#df8f9c",
  "#a8cb73",
];
function el(tag, text, parent, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  if (parent) parent.append(node);
  return node;
}
function button(text, action, parent) {
  const node = el("button", text, parent);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function select(label, values, current, action, parent = $("controls")) {
  const wrapper = el("label", label, parent),
    node = el("select", undefined, wrapper);
  for (const value of values) {
    const item = Array.isArray(value) ? value : [value, value];
    const option = el("option", item[1], node);
    option.value = item[0];
  }
  node.value = current;
  node.addEventListener("change", () => action(node.value));
  return node;
}
function raw(value, parent = $("detail"), title = "Full source payload") {
  const fold = el("details", undefined, parent);
  el("summary", title, fold);
  el("pre", json(value), fold);
  return fold;
}
function message(text, parent = $("detail"), type = "hint") {
  return el("p", text, parent, type);
}
function details(title, value) {
  $("detail-title").textContent = title;
  $("detail").replaceChildren();
  raw(value);
}
function graph() {
  return D.graphs.find((item) => item.id === state.graph) || D.graphs[0];
}
function fields(value, key, found = []) {
  if (Array.isArray(value)) {
    for (const item of value) fields(item, key, found);
  } else if (value && typeof value === "object") {
    for (const [name, item] of Object.entries(value)) {
      if (name === key) found.push(...(Array.isArray(item) ? item : [item]));
      else fields(item, key, found);
    }
  }
  return found;
}
function unique(values) {
  return [...new Set(values.filter((item) => typeof item === "string"))].sort();
}
function provenanceRecords(value, source, result) {
  if (Array.isArray(value)) {
    for (const item of value) provenanceRecords(item, source, result);
  } else if (value && typeof value === "object") {
    if (value.id && value.provider && value.model) {
      result.set(value.id, { ...value, source_artifact: source });
    }
    for (const item of Object.values(value))
      provenanceRecords(item, source, result);
  }
}
const provenanceIndex = new Map();
for (const [source, artifact] of Object.entries(D.artifacts)) {
  provenanceRecords(artifact.value, source, provenanceIndex);
}
function allRows() {
  const g = graph(),
    assertions = new Map(g.enriched.assertions.map((row) => [row.id, row])),
    evidence = new Map(g.enriched.evidence.map((row) => [row.id, row]));
  return (g.tables.nodes || []).map((node) => {
    const a = assertions.get(node.id),
      e = evidence.get(node.id);
    const semantic = (g.tables.semantic_nodes || []).find((row) => row.id === node.id)?.payload;
    const quotes = (g.tables.semantic_quotes || [])
      .filter((row) => row.owner_kind === "node" && row.owner_id === node.id)
      .map((row) => row.payload);
    const support = (g.tables.support || [])
      .filter((row) => row.assertion_id === node.id)
      .map((row) => evidence.get(row.evidence_id))
      .filter(Boolean);
    const ids = a?.provenance_ids || [];
    const provenance = (g.tables.evidence_service_state || [])
      .filter((row) => row.name === "provenance")
      .flatMap((row) => (Array.isArray(row.payload) ? row.payload : []))
      .filter((row) => ids.includes(row.id));
    for (const id of ids) {
      const record = provenanceIndex.get(id);
      if (record && !provenance.some((item) => item.id === id))
        provenance.push(record);
    }
    const origin = (item) =>
      item?.source_kind ||
      (item?.kind === "code"
        ? "code"
        : item?.kind === "docs"
          ? "document"
          : item?.kind);
    return {
      ...node,
      source_kind: unique([origin(e), ...support.map(origin)]),
      assertion: a,
      evidence: e,
      semantic,
      quotes,
      support,
      provenance,
    };
  });
}
function searched(rows) {
  const q = state.query.toLocaleLowerCase();
  return rows.filter(
    (row) => !q || compact(row).toLocaleLowerCase().includes(q),
  );
}
function table(rows, columns, onSelect, parent = $("listing")) {
  const pageSize = 75,
    maxPage = Math.max(0, Math.ceil(rows.length / pageSize) - 1);
  state.page = Math.min(state.page, maxPage);
  const bar = el("div", undefined, parent, "paging");
  button(
    "Previous",
    () => {
      state.page = Math.max(0, state.page - 1);
      renderBody();
    },
    bar,
  ).disabled = state.page === 0;
  el(
    "span",
    `${rows.length} matching records  |  Page ${state.page + 1} / ${maxPage + 1}`,
    bar,
  );
  button(
    "Next",
    () => {
      state.page = Math.min(maxPage, state.page + 1);
      renderBody();
    },
    bar,
  ).disabled = state.page === maxPage;
  const grid = el("table", undefined, parent, "row-list"),
    head = el("tr", undefined, el("thead", undefined, grid));
  for (const [name] of columns) el("th", name, head);
  const body = el("tbody", undefined, grid);
  for (const row of rows.slice(
    state.page * pageSize,
    (state.page + 1) * pageSize,
  )) {
    const tr = el("tr", undefined, body);
    columns.forEach(([name, value], index) => {
      const cell = el("td", undefined, tr),
        text = String(value(row) ?? "Not recorded");
      if (index === 0) button(text, () => onSelect(row), cell);
      else el("span", text, cell);
    });
  }
  if (!rows.length)
    message(
      "No matching records. Reset filters or select another source.",
      parent,
      "empty",
    );
}
function commonControls() {
  const label = el("label", "Search complete records", $("controls")),
    input = el("input", undefined, label);
  input.type = "search";
  input.value = state.query;
  input.placeholder = "ID, text, path, provider... ";
  input.addEventListener("input", () => {
    state.query = input.value;
    state.page = 0;
    renderBody();
  });
  button(
    "Reset filters",
    () => {
      state.query = "";
      state.filters = {};
      state.hops = 0;
      state.page = 0;
      render();
    },
    $("controls"),
  );
}
function sourceLink(id, parent = $("detail"), label = id) {
  button(
    label,
    () => {
      state.view = "graph";
      state.selected = id;
      state.hops = 0;
      render();
      selectNode(id);
    },
    parent,
  );
}
function selectNode(id) {
  if (state.graphMode !== "topology") state.graphMode = "neighborhood";
  state.neighborLimit = 8;
  const g = graph(),
    row = allRows().find((item) => item.id === id);
  details(
    row ? `${row.name}  |  ${id.slice(0, 12)}` : id,
    row || { id, status: "No match in selected graph revision" },
  );
  if (row) {
    const summary = el("div", undefined, undefined, "card");
    $("detail").prepend(summary);
    el(
      "p",
      row.assertion?.statement || row.evidence?.text || row.name,
      summary,
    );
    for (const key of [
      "modality",
      "operator",
      "scope",
      "conditions",
      "exceptions",
      "categories",
      "relevance",
      "temporal_status",
      "review_status",
      "status",
      "description",
      "preserved_conditions",
      "preserved_exceptions",
    ]) {
      const value = row.semantic?.[key] ?? row.assertion?.[key] ?? row.evidence?.[key];
      if (value !== undefined) message(`${key}: ${compact(value)}`, summary);
    }
    for (const p of row.provenance || [])
      message(
        `${p.provider} / ${p.model}  |  ${p.verifier || p.review_status || "review status not recorded"}`,
        summary,
      );
    if (row.evidence)
      message(
        `Source: ${row.evidence.path}  |  ${compact(row.evidence.locator || { start_line: row.evidence.start_line, end_line: row.evidence.end_line })}`,
        summary,
      );
  }
  state.selected = id;
  setHash();
  if (!row) return;
  const target = $("detail");
  el("h3", "Stored incoming / outgoing edges", target);
  const edges = (g.tables.edges || []).filter(
    (edge) => edge.source_id === id || edge.target_id === id,
  );
  for (const edge of edges) {
    const block = el("div", undefined, target, "card");
    el("p", `${edge.type}  |  ${edge.method}`, block);
    sourceLink(edge.source_id, block, nodeLabel(edge.source_id));
    el("span", "  ->  ", block);
    sourceLink(edge.target_id, block, nodeLabel(edge.target_id));
    raw(edge, block);
    for (const relation of g.tables.semantic_edges || []) {
      if (relation.source_id === edge.source_id && relation.target_id === edge.target_id && relation.type === edge.type) {
        if (relation.payload?.description) el("p", relation.payload.description, block);
        if (relation.payload?.status) message(`Interpretation: ${relation.payload.status}`, block);
        raw(relation.payload, block, "Exact source quotes supporting this relation");
      }
    }
  }
  if (row.quotes?.length) {
    el("h3", "Exact source quotations", target);
    for (const quote of row.quotes) {
      const card = el("div", undefined, target, "card");
      const evidence = g.enriched.evidence.find((item) => item.id === quote.evidence_id);
      sourceLink(quote.evidence_id, card, evidence?.path || quote.evidence_id);
      el("pre", quote.text, card);
      message(`Source-span characters ${quote.start}-${quote.end} (end exclusive)`, card);
      raw({ ...quote, file_hash: evidence?.file_hash, locator: evidence?.locator }, card, "Source identity and exact locator");
    }
  }
  el("h3", "Original evidence", target);
  for (const evidence of row.support || []) {
    const card = el("div", undefined, target, "card");
    sourceLink(
      evidence.id,
      card,
      `${evidence.label || evidence.id}  |  ${evidence.path}`,
    );
    el("pre", evidence.text, card);
    raw(evidence, card, "Locator, hashes and provenance");
  }
  el("h3", "Verified relations (complete evidence IDs)", target);
  for (const relation of g.tables.verified_relations || []) {
    if ([relation.payload?.source_id, relation.payload?.target_id].includes(id))
      raw(relation, target);
  }
  el("h3", "Derived trace references", target);
  message(
    "These reference matches are inspector-derived links, not stored edges. Only candidate graph_revision bindings confirm revision association.",
    target,
  );
  for (const [key, artifact] of Object.entries(D.artifacts)) {
    if (compact(artifact.value || "").includes(id))
      button(
        `Artifact ${key.slice(0, 16)}... `,
        () => selectArtifact(key),
        target,
      );
  }
  for (const candidate of D.candidates) {
    const audit = candidate.files["audit.json"]?.value || {};
    const placements = asRecords(audit.placements).filter((item) =>
      (item.obligation_ids || []).includes(id),
    );
    for (const placement of placements)
      button(
        `Passage  |  ${candidate.id.slice(0, 12)}  |  ${placement.section}`,
        () => selectPassage(candidate, placement),
        target,
      );
  }
  if (state.view === "graph") {
    if (state.graphMode === "topology" && topologyView) topologyView.select(id);
    else drawGraph();
    $("visual").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
function nodeFilters(row) {
  for (const [key, wanted] of Object.entries(state.filters)) {
    if (wanted && !fields(row, key).includes(wanted)) return false;
  }
  return true;
}
function graphControls() {
  select(
    "Graph revision",
    D.graphs.map((item) => [
      item.id,
      item.kind === "current"
        ? "Current run graph"
        : `Frozen ${item.id.slice(0, 20)}... `,
    ]),
    state.graph,
    (value) => {
      state.graph = value;
      state.selected = null;
      state.filters = {};
      state.page = 0;
      render();
    },
  );
  select(
    "Table",
    [
      "nodes",
      "edges",
      "assertions",
      "evidence",
      "support",
      "verified_relations",
      "evidence_service_state",
      "semantic_nodes",
      "semantic_edges",
      "semantic_quotes",
      "semantic_batches",
    ],
    state.table,
    (value) => {
      state.table = value;
      state.page = 0;
      render();
    },
  );
  commonControls();
  const rows = allRows();
  const advanced = el("details", undefined, $("controls"), "advanced-filters");
  el("summary", "Filters and table neighborhood", advanced);
  const filterControls = el("div", undefined, advanced, "filter-controls");
  for (const [key, label] of [
    ["type", "Node type"],
    ["source_kind", "Origin"],
    ["categories", "Category"],
    ["relevance", "Relevance"],
    ["temporal_status", "Temporal status"],
    ["review_status", "Review"],
    ["provider", "Provider"],
  ]) {
    const values = unique(rows.flatMap((row) => fields(row, key)));
    if (values.length)
      select(
        label,
        [["", "All"], ...values],
        state.filters[key] || "",
        (value) => {
          state.filters[key] = value;
          state.page = 0;
          renderBody();
        },
        filterControls,
      );
  }
  for (const key of ["edge_type", "method"]) {
    const field = key === "edge_type" ? "type" : key,
      values = unique((graph().tables.edges || []).map((row) => row[field]));
    if (values.length)
      select(
        key === "edge_type" ? "Relation type" : "Relation method",
        [["", "All"], ...values],
        state.filters[key] || "",
        (value) => {
          state.filters[key] = value;
          state.page = 0;
          renderBody();
        },
        filterControls,
      );
  }
  select(
    "Table neighborhood",
    [
      [0, "All matching nodes"],
      [1, "One hop"],
      [2, "Two hops"],
    ],
    state.hops,
    (value) => {
      state.hops = Number(value);
      state.page = 0;
      renderBody();
    },
    filterControls,
  );
}
function matchingNodes() {
  let rows = searched(allRows()).filter((row) =>
    nodeFilters({
      ...row,
      edge_type: state.filters.edge_type,
      method: state.filters.method,
    }),
  );
  const edges = (graph().tables.edges || []).filter(
    (edge) =>
      (!state.filters.edge_type || edge.type === state.filters.edge_type) &&
      (!state.filters.method || edge.method === state.filters.method),
  );
  if (state.filters.edge_type || state.filters.method) {
    const ids = new Set(
      edges.flatMap((edge) => [edge.source_id, edge.target_id]),
    );
    rows = rows.filter((row) => ids.has(row.id));
  }
  if (state.hops && state.selected) {
    const ids = new Set([state.selected]);
    for (let hop = 0; hop < state.hops; hop++) {
      const added = edges
        .filter((edge) => ids.has(edge.source_id) || ids.has(edge.target_id))
        .flatMap((edge) => [edge.source_id, edge.target_id]);
      added.forEach((id) => ids.add(id));
    }
    rows = rows.filter((row) => ids.has(row.id));
  }
  return rows;
}
function graphBody() {
  const g = graph(),
    rows = matchingNodes();
  $("summary").textContent =
    `Revision: ${g.id}  |  Loaded ${g.tables.nodes?.length || 0} nodes / ${g.tables.edges?.length || 0} stored edges  |  Matching ${rows.length} nodes`;
  drawGraph();
  if (state.table === "nodes")
    table(
      rows,
      [
        ["Node", (r) => nodeLabel(r.id)],
        ["Type", (r) => r.type],
        ["Source / scope", (r) => r.evidence?.path || r.assertion?.scope || r.scope || r.id],
      ],
      (r) => selectNode(r.id),
    );
  else {
    let values = g.tables[state.table] || [];
    if (["assertions", "evidence"].includes(state.table))
      values = g.enriched[state.table];
    values = searched(values);
    if (state.table === "edges")
      values = values.filter(
        (row) =>
          (!state.filters.edge_type || row.type === state.filters.edge_type) &&
          (!state.filters.method || row.method === state.filters.method),
      );
    table(
      values,
      [
        ["Record", (r) => r.id || r.name || r.source_id || r.assertion_id],
        ["Details", (r) => compact(r)],
      ],
      (r) => {
        details(`${state.table} record`, r);
        for (const id of [
          r.id,
          r.source_id,
          r.target_id,
          r.assertion_id,
          r.evidence_id,
          ...(r.payload?.evidence_ids || []),
        ].filter(Boolean))
          sourceLink(id);
      },
    );
  }
  message(
    "All records remain available in the tables. Table pagination never hides connections in the neighborhood view.",
    $("listing"),
  );
}
function nodeLabel(id) {
  const g = graph(),
    node = (g.tables.nodes || []).find((row) => row.id === id),
    fact = g.enriched.assertions.find((row) => row.id === id),
    evidence = g.enriched.evidence.find((row) => row.id === id);
  if (fact) return fact.statement;
  if (evidence) {
    const lines = evidence.start_line == null ? "" : `:${evidence.start_line}-${evidence.end_line ?? evidence.start_line}`;
    return `${evidence.label || "Source"} | ${evidence.path}${lines}`;
  }
  return node?.name || id;
}
function graphOverview(parent) {
  const g = graph(), profile = g.profile;
  el("h2", "What is in this graph?", parent);
  message("Start with the relation map, or search below and select a fact to follow its evidence. Counts include the entire selected revision.", parent);
  if (!profile) return message("Re-export this run to include graph diagnostics.", parent);
  const stats = el("div", undefined, parent, "graph-stats");
  for (const [value, label] of [
    [g.tables.nodes?.length || 0, "nodes"],
    [g.tables.edges?.length || 0, "stored edges"],
    [profile.components.length, "connected components"],
    [`${profile.supported_assertions}/${profile.assertion_count}`, "facts with recorded evidence"],
  ]) {
    const card = el("div", undefined, stats, "card");
    el("strong", value, card, "stat");
    message(label, card);
  }
  const types = el("div", undefined, parent, "links");
  for (const [type, count] of Object.entries(profile.node_types)) {
    button(`${type} (${count})`, () => {
      state.filters = { type };
      state.query = "";
      state.table = "nodes";
      state.page = 0;
      render();
      $("listing").scrollIntoView({ behavior: "smooth", block: "start" });
    }, types);
  }
  el("h3", "Relation map", parent);
  message("Each row aggregates stored edges with the same endpoint types, relation and method. Select a row to inspect a concrete connection. Arrows run from source to target.", parent);
  const map = el("div", undefined, parent, "relation-map");
  for (const relation of profile.relations) {
    const row = button("", () => {
      state.filters = { edge_type: relation.type, method: relation.method };
      const nodes = new Map((g.tables.nodes || []).map((node) => [node.id, node]));
      const edge = (g.tables.edges || []).find((item) =>
        item.type === relation.type && item.method === relation.method &&
        nodes.get(item.source_id)?.type === relation.source_type &&
        nodes.get(item.target_id)?.type === relation.target_type,
      );
      state.query = "";
      state.page = 0;
      state.selected = edge?.source_id || null;
      state.graphMode = "neighborhood";
      render();
      if (state.selected) selectNode(state.selected);
    }, map);
    row.className = "relation-row";
    el("span", relation.source_type, row, "relation-endpoint");
    const connector = el("span", undefined, row, "relation-connector");
    el("strong", `${relation.type} ->`, connector);
    el("small", relation.method, connector);
    el("span", relation.target_type, row, "relation-endpoint");
    el("strong", relation.count, row, "relation-count");
  }
  if (!profile.relations.length) message("No stored edges in this revision.", map);
  const health = el("div", undefined, parent, "card");
  el("h3", "Graph checks", health);
  for (const [label, ids] of [
    ["Isolated nodes", profile.isolated_ids],
    ["Facts without a valid support-table evidence link", profile.unsupported_assertion_ids],
  ]) {
    const fold = el("details", undefined, health);
    el("summary", `${label}: ${ids.length}`, fold);
    for (const id of ids) sourceLink(id, fold, nodeLabel(id));
  }
  message(`Edges with missing endpoints: ${profile.dangling_edge_indices.length}. Largest connected component: ${profile.components[0]?.length || 0} nodes.`, health,
    profile.dangling_edge_indices.length ? "warning" : "hint");
  message(profile.interpretation, health);
}
function neighborhood(parent) {
  const g = graph(),
    rows = new Map(allRows().map((row) => [row.id, row])),
    selected = rows.get(state.selected);
  el("h2", "Follow one connection at a time", parent);
  if (!selected) {
    message("Select a node from the search results below, or choose a relation from the overview.", parent, "empty");
    return;
  }
  const edges = (g.tables.edges || []).filter((edge) =>
    (!state.filters.edge_type || edge.type === state.filters.edge_type) &&
    (!state.filters.method || edge.method === state.filters.method),
  );
  const incoming = edges.filter((edge) => edge.target_id === selected.id),
    outgoing = edges.filter((edge) => edge.source_id === selected.id);
  message("Direct connections across the entire revision, independent of search results and table pages. Relation filters apply here; node filters apply to the table below. Select a connected node to move through the graph.", parent);
  if (state.filters.edge_type || state.filters.method)
    button("Show all relation types and methods", () => {
      delete state.filters.edge_type;
      delete state.filters.method;
      render();
    }, parent);
  const lanes = el("div", undefined, parent, "neighborhood");
  const lane = (title) => {
    const column = el("section", undefined, lanes, "graph-lane");
    el("h3", title, column);
    return column;
  };
  const before = lane(`Incoming (${incoming.length})`),
    center = lane("Selected node"),
    after = lane(`Outgoing (${outgoing.length})`);
  const nodeCard = (id, container, focus = false) => {
    const row = rows.get(id), card = el("article", undefined, container, focus ? "graph-node focused" : "graph-node");
    el("span", row?.type || "Missing endpoint", card, "eyebrow");
    if (focus) el("p", nodeLabel(id), card, "node-name");
    else button(nodeLabel(id), () => selectNode(id), card);
    if (row?.assertion?.subject) message(`Subject: ${row.assertion.subject}`, card);
    if (row?.evidence) message(row.evidence.text || "No source text recorded", card, "evidence-preview");
    if (row?.support.length) message(`${row.support.length} original evidence records`, card);
    if (focus) {
      message(id, card, "node-identity");
      button("Read evidence and provenance", () => {
        selectNode(id);
        $("detail-title").scrollIntoView({ behavior: "smooth", block: "start" });
      }, card);
    }
    return card;
  };
  nodeCard(selected.id, center, true);
  const addEdges = (values, container, endpoint) => {
    for (const edge of values.slice(0, state.neighborLimit)) {
      const card = nodeCard(edge[endpoint], container),
        relation = el("div", undefined, card, "edge-description");
      el("strong", `${edge.type} ->`, relation);
      message(`Method: ${edge.method || "Not recorded"}`, relation);
      if (edge.evidence_id) sourceLink(edge.evidence_id, relation, "Open relation evidence");
      raw(edge, relation, "Stored edge record");
    }
    if (!values.length) message("No matching stored edges.", container, "empty");
    if (values.length > state.neighborLimit)
      button(`Show more (${values.length - state.neighborLimit} remaining)`, () => {
        state.neighborLimit += 8;
        drawGraph();
      }, container);
  };
  addEdges(incoming, before, "source_id");
  addEdges(outgoing, after, "target_id");
  message("Incoming: connected node -> selected node. Outgoing: selected node -> connected node. Repeated cards preserve parallel edges and their separate methods/evidence. Self-relations appear in both directions.", parent);
}
function drawGraph() {
  if (state.view !== "graph") return;
  const parent = $("visual");
  parent.replaceChildren();
  const modes = el("div", undefined, parent, "graph-modes");
  for (const [mode, label] of [["topology", "Interactive graph"], ["overview", "Graph overview"], ["neighborhood", "Node and evidence"]]) {
    const item = button(label, () => {
      state.graphMode = mode;
      drawGraph();
    }, modes);
    item.classList.toggle("active", state.graphMode === mode);
    item.setAttribute("aria-pressed", String(state.graphMode === mode));
  }
  topologyView = null;
  if (state.graphMode === "topology") {
    const nodes = matchingNodes(), ids = new Set(nodes.map((node) => node.id));
    const edges = (graph().tables.edges || []).filter((edge) =>
      ids.has(edge.source_id) && ids.has(edge.target_id) &&
      (!state.filters.edge_type || edge.type === state.filters.edge_type) &&
      (!state.filters.method || edge.method === state.filters.method)).map((edge) => {
        const interpretation = (graph().tables.semantic_edges || []).find((item) =>
          item.source_id === edge.source_id && item.target_id === edge.target_id && item.type === edge.type)?.payload;
        return { ...edge, ...(interpretation || {}) };
      });
    if (!nodes.length) { message("No nodes match the filters. Reset filters to show the complete graph.", parent); return; }
    topologyView = createTopology(parent, {
      nodes, edges, label: nodeLabel, selected: state.selected,
      key: JSON.stringify([state.graph, nodes.map((node) => node.id), state.filters]),
      onSelect: selectNode,
      onEdge: (edge) => {
        details(`${edge.type}: ${nodeLabel(edge.source_id)} -> ${nodeLabel(edge.target_id)}`, edge);
        if (edge.description) el("p", edge.description, $("detail"));
        if (edge.status) message(`Interpretation: ${edge.status}`, $("detail"));
        sourceLink(edge.source_id, $("detail"), "Source: " + nodeLabel(edge.source_id));
        sourceLink(edge.target_id, $("detail"), "Target: " + nodeLabel(edge.target_id));
        const evidence = graph().enriched.evidence.find((item) => item.id === edge.evidence_id);
        if (evidence) { el("h3", "Original edge evidence", $("detail")); el("pre", evidence.text, $("detail")); raw(evidence); }
      },
    });
  } else if (state.graphMode === "overview") graphOverview(parent);
  else neighborhood(parent);
}
function runControls() {
  select(
    "Recorded source",
    [
      "stages",
      "events",
      "checkpoints",
      "writes",
      "charges",
      "run manifest",
      "run result",
    ],
    state.runSource || "stages",
    (value) => {
      state.runSource = value;
      state.page = 0;
      render();
    },
  );
  commonControls();
}
function differences(before, after, path = "$", result = []) {
  if (compact(before) === compact(after)) return result;
  if (
    before &&
    after &&
    typeof before === "object" &&
    typeof after === "object" &&
    !Array.isArray(before) &&
    !Array.isArray(after)
  ) {
    for (const key of new Set([...Object.keys(before), ...Object.keys(after)]))
      differences(before[key], after[key], `${path}.${key}`, result);
  } else
    result.push({
      path,
      before: before === undefined ? "[absent]" : before,
      after: after === undefined ? "[absent]" : after,
    });
  return result;
}
function stageDetail(row) {
  details(row.id, row);
  const value = row.result?.value || {};
  message(
    `Stage: ${value.stage || row.manifest.value?.stage}  |  Item: ${value.item || row.manifest.value?.item || "inventory"}  |  Status / route: ${value.outputs?.status || row.manifest.value?.status || value.outputs?.route || "Recorded"}`,
  );
  raw(value.inputs, $("detail"), "Exact input state");
  raw(value.outputs, $("detail"), "Exact output state");
  el("h3", "All revisions of this stage item", $("detail"));
  const siblings = D.stages.filter(
    (item) =>
      item.manifest.value?.stage === row.manifest.value?.stage &&
      item.manifest.value?.item === row.manifest.value?.item &&
      item.result,
  );
  for (const sibling of siblings)
    button(sibling.id, () => stageDetail(sibling), $("detail"));
  if (siblings.length > 1)
    select(
      "Compare selected revision with",
      [
        ["", "Choose revision"],
        ...siblings
          .filter((item) => item !== row)
          .map((item) => [item.id, item.id]),
      ],
      "",
      (id) => {
        const previous = siblings.find((item) => item.id === id);
        if (previous)
          raw(
            differences(previous.result.value, value),
            $("detail"),
            `Changes from ${id}`,
          ).open = true;
      },
      $("detail"),
    );
  el("h3", "Referenced artifacts", $("detail"));
  for (const ref of D.trace_links.filter((item) => item.origin === row.id))
    button(
      `${ref.field}  |  ${ref.target.slice(0, 16)}... `,
      () => {
        if (ref.kind === "candidate_reference") {
          state.view = "content";
          state.contentSource = ref.target;
          state.page = 0;
          render();
        } else if (ref.kind === "ledger_reference") {
          details("Recorded usage reference", {
            reference: ref,
            charges: (D.costs.charges || []).filter(
              (item) => item.id === ref.target,
            ),
          });
        } else selectArtifact(ref.target);
      },
      $("detail"),
    );
  el("h3", "Recorded activity for this stage", $("detail"));
  message(
    "Stage-name association only; timestamps and revisions are not inferred.",
  );
  for (const event of D.events.filter(
    (item) => item.record.stage === value.stage,
  ))
    raw(event, $("detail"), `Event ${event.line}  |  ${event.record.event}`);
}
function runOutcome(parent) {
  const record = D.run_files["live-result.json"];
  if (!record) return;
  const value = record.value;
  const card = el("div", undefined, parent, "card");
  el("h3", "Recorded execution result", card);
  if (value && typeof value === "object" && !Array.isArray(value)) {
    message(`Last recorded state: ${value.status || "Not recorded"}`, card);
    if (value.error) {
      message(`Execution error: ${compact(value.error)}`, card, "warning");
      message(
        "The recorded state is not a successful completion result.",
        card,
      );
    }
    message(
      `Next recorded nodes: ${compact(value.next ?? "Not recorded")}`,
      card,
    );
    message(
      `Recorded interrupts: ${compact(value.interrupts ?? "Not recorded")}`,
      card,
    );
  } else
    message("Structured execution result is unavailable.", card, "warning");
  raw(record, card, "live-result.json: complete recorded state and error");
}
function runBody() {
  const source = state.runSource || "stages";
  let rows = [];
  if (source === "stages") rows = D.stages;
  else if (source === "events") rows = D.events;
  else if (source === "run manifest") rows = [D.run_manifest];
  else if (source === "run result")
    rows = D.run_files["live-result.json"]
      ? [D.run_files["live-result.json"]]
      : [];
  else rows = D.checkpoints[source] || D.costs[source] || [];
  $("summary").textContent =
    `${rows.length} recorded ${source}  |  Step numbers are historical identifiers, not execution order. Event line order is preserved. Checkpoints have no inferred stage binding.`;
  runOutcome($("visual"));
  if (source === "charges") {
    const charges = D.costs.charges || [],
      sum = (status, column) =>
        charges
          .filter((row) => row.status === status)
          .reduce((total, row) => total + Number(row[column] || 0), 0);
    message(
      `Selected run only  |  Settled PLN ${sum("settled", "charged").toFixed(6)}  |  Uncertain PLN ${sum("uncertain", "charged").toFixed(6)}  |  Active reserved PLN ${sum("reserved", "reserved").toFixed(6)}. Source: charges table; event and stage costs are not added.`,
      $("visual"),
    );
  }
  if (source === "stages")
    table(
      searched(rows),
      [
        [
          "Stage / item / revision",
          (r) =>
            `${r.result?.value?.stage || r.manifest.value?.stage || "Unknown stage"}  |  ${r.id}`,
        ],
        [
          "Status / route",
          (r) =>
            r.result?.value?.outputs?.status ||
            r.manifest.value?.status ||
            r.result?.value?.outputs?.route ||
            "Recorded output",
        ],
        ["Integrity", (r) => r.result?.status || r.manifest.status],
      ],
      stageDetail,
    );
  else
    table(
      searched(rows),
      [
        [
          "Record",
          (r) => r.line || r.checkpoint_id || r.task_id || r.id || r.path,
        ],
        [
          "Event / status / parent",
          (r) =>
            r.record?.event || r.status || r.parent_checkpoint_id || "Recorded",
        ],
        ["Details", (r) => compact(r)],
      ],
      (r) => details(source, r),
    );
}
function contentRecords() {
  const records = Object.entries(D.artifacts).map(([id, value]) => ({
    id,
    kind: "artifact",
    ...value,
  }));
  for (const candidate of D.candidates)
    for (const [name, value] of Object.entries(candidate.files))
      records.push({
        id: `${candidate.id}/${name}`,
        kind: "candidate",
        candidate: candidate.id,
        ...value,
      });
  return records;
}
function selectArtifact(id) {
  const artifact = D.artifacts[id];
  details(`Artifact ${id}`, artifact);
  el("h3", "Recorded reference origins", $("detail"));
  for (const link of D.trace_links.filter((item) => item.target === id)) {
    const stage = D.stages.find((item) => item.id === link.origin);
    button(
      `${link.origin}  |  ${link.field}`,
      () => (stage ? stageDetail(stage) : details("Reference origin", link)),
      $("detail"),
    );
  }
  if (artifact?.value) {
    el("h3", "Text / Markdown source", $("detail"));
    const text =
      typeof artifact.value === "string"
        ? artifact.value
        : fields(artifact.value, "markdown").concat(
            fields(artifact.value, "statement"),
          );
    el("pre", typeof text === "string" ? text : json(text), $("detail"));
  }
}
function selectPassage(candidate, placement) {
  details(`Passage  |  ${placement.section || placement.id}`, placement);
  const source = candidate.files["documentation/index.md"]?.value,
    audit = candidate.files["audit.json"]?.value || {},
    codepoints = typeof source === "string" ? Array.from(source) : [];
  const valid =
    Number.isInteger(placement.start) &&
    Number.isInteger(placement.end) &&
    placement.start >= 0 &&
    placement.end >= placement.start &&
    placement.end <= codepoints.length &&
    codepoints.slice(placement.start, placement.end).join("") ===
      placement.passage;
  message(
    valid
      ? "Offsets verified against the exact candidate text (Unicode code points)."
      : "Offset mismatch or unavailable source. No passage is highlighted.",
    $("detail"),
    valid ? "hint" : "warning",
  );
  if (valid) {
    const pre = el("pre", undefined, $("detail"));
    pre.append(
      document.createTextNode(
        codepoints
          .slice(Math.max(0, placement.start - 200), placement.start)
          .join(""),
      ),
    );
    el("mark", placement.passage, pre);
    pre.append(
      document.createTextNode(
        codepoints.slice(placement.end, placement.end + 200).join(""),
      ),
    );
  }
  message(
    `Candidate graph revision: ${audit.graph_revision || "Not recorded"}`,
  );
  if (
    audit.graph_revision &&
    D.graphs.some((item) => item.id === audit.graph_revision)
  ) {
    state.graph = audit.graph_revision;
    message("Fact links use the candidate's recorded frozen graph revision.");
    for (const id of placement.obligation_ids || []) sourceLink(id);
  } else
    message(
      "Graph revision association unavailable. IDs remain in the raw record; no confirmed graph match is inferred.",
    );
}
function contentControls() {
  select(
    "Content source",
    [
      ["all", "All objects and candidate files"],
      ...D.candidates.map((item) => [
        item.id,
        `Candidate ${item.id.slice(0, 20)}... `,
      ]),
    ],
    state.contentSource || "all",
    (value) => {
      state.contentSource = value;
      state.page = 0;
      render();
    },
  );
  commonControls();
}
function contentBody() {
  const records = contentRecords().filter(
    (row) =>
      !state.contentSource ||
      state.contentSource === "all" ||
      row.candidate === state.contentSource,
  );
  $("summary").textContent =
    `${records.length} resolved content records  |  Binary content has metadata only. Markdown, HTML and Mermaid remain inert source text.`;
  if (state.contentSource && state.contentSource !== "all") {
    const candidate = D.candidates.find(
      (item) => item.id === state.contentSource,
    );
    const placements = asRecords(
      candidate?.files["audit.json"]?.value?.placements,
    );
    el("h3", `${placements.length} final passage placements`, $("visual"));
    for (const placement of placements)
      button(
        `${placement.section}  |  ${placement.id}`,
        () => selectPassage(candidate, placement),
        $("visual"),
      );
  }
  table(
    searched(records),
    [
      ["Artifact / file", (r) => r.id],
      ["Type / integrity", (r) => `${r.format || "unavailable"} / ${r.status}`],
      ["Bytes", (r) => r.size],
    ],
    (row) => {
      if (row.kind === "artifact") selectArtifact(row.id);
      else details(row.id, row);
      if (row.format === "text") el("pre", row.value, $("detail"));
      if (row.format === "json") {
        const text = fields(row.value, "markdown");
        if (text.length) el("pre", text.join("\n\n"), $("detail"));
      }
      const compare = select(
        "Compare content with",
        [
          ["", "Choose content record"],
          ...records
            .filter((item) => item.id !== row.id)
            .map((item) => [item.id, item.id]),
        ],
        "",
        (id) => {
          const previous = records.find((item) => item.id === id);
          if (previous)
            raw(
              differences(previous.value, row.value),
              $("detail"),
              "Content changes",
            ).open = true;
        },
        $("detail"),
      );
      compare.setAttribute("aria-label", "Compare content with");
    },
  );
}
function qualityRecords() {
  const rows = D.diagnostics.map((value, index) => ({
    id: `diagnostic:${index + 1}`,
    source: value.source,
    kind: "Integrity diagnostic",
    value,
  }));
  for (const [name, record] of Object.entries(D.run_files))
    if (/coverage|audit|graph-manifest|exclusion|live-result/.test(name))
      rows.push({
        id: name,
        source: name,
        kind:
          name === "live-result.json"
            ? "Recorded execution result"
            : "Recorded quality report",
        value: record.value,
      });
  for (const stage of D.stages) {
    const name =
      stage.result?.value?.stage || stage.manifest.value?.stage || "";
    if (/audit|verif|aspect|issue|review|exclu/.test(name))
      rows.push({
        id: stage.id,
        source: stage.id,
        kind: name,
        value: stage.result?.value || stage.manifest.value,
      });
  }
  for (const candidate of D.candidates) {
    const audit = candidate.files["audit.json"];
    if (audit)
      rows.push({
        id: `candidate:${candidate.id}`,
        source: `candidate:${candidate.id}/audit.json`,
        kind: "Final candidate audit",
        value: audit.value,
      });
  }
  return rows;
}
function qualityControls() {
  commonControls();
}
function qualityBody() {
  const rows = qualityRecords();
  $("summary").textContent =
    `${rows.length} recorded reports and diagnostics. Each source retains its own denominator and result. Using every discovered graph fact does not establish complete source discovery.`;
  runOutcome($("visual"));
  const files = D.run_files,
    coverage = files["source-coverage.json"]?.value;
  const card = el("div", undefined, $("visual"), "card");
  el("h3", "Source discovery / final coverage", card);
  if (coverage) {
    for (const key of ["aspects", "qualifiers", "blocks", "facts_in_text"])
      message(
        `${key}: ${compact(coverage[key] ?? "Not available")}  |  source: source-coverage.json`,
        card,
      );
    message(
      `Recorded complete result: ${String(coverage.complete)}. This is the recorded audit result, not a new independent quality guarantee.`,
      card,
    );
    raw(coverage, card, "Full coverage and unresolved items");
  } else
    message(
      "Source-aspect / source-to-document audit: not available. No completeness percentage is inferred.",
      card,
      "warning",
    );
  const g = graph(),
    facts = g.tables.assertions || [],
    selectedCandidate = D.candidates.filter(
      (item) => item.files["audit.json"]?.value?.graph_revision === g.id,
    );
  el("h3", "Graph utilization for selected revision", card);
  message(
    `Revision ${g.id}  |  ${facts.length} stored facts (denominator: assertions table).`,
    card,
  );
  const utilization = D.quality?.utilization.find(
    (item) => item.graph_revision === g.id,
  );
  if (utilization) {
    for (const key of ["retrieved", "assigned"]) {
      const values = utilization[key];
      message(
        `${key}: ${values === null ? "Not available" : `${values.length} / ${utilization.denominator} graph facts`}. Denominator: ${utilization.denominator_source}`,
        card,
      );
      if (values !== null)
        raw(
          {
            ids: values,
            sources:
              utilization[
                key === "retrieved" ? "retrieval_sources" : "assignment_sources"
              ],
          },
          card,
          `${key} fact IDs and source records`,
        );
    }
  }
  if (!selectedCandidate.length)
    message(
      "No candidate is durably bound to this selected graph revision. Select its frozen revision in Graph to inspect utilization.",
      card,
    );
  for (const candidate of selectedCandidate) {
    const audit = candidate.files["audit.json"].value,
      mapped = new Set(
        asRecords(audit.mappings).map((item) => item.obligation_id),
      ),
      unused = facts.filter((item) => !mapped.has(item.id));
    message(
      `Candidate ${candidate.id.slice(0, 16)}  |  ${facts.filter((item) => mapped.has(item.id)).length} mapped / ${facts.length} graph facts  |  ${unused.length} unutilized. Source: audit.json mappings + selected assertions table.`,
      card,
    );
    raw(unused, card, "Unutilized facts");
  }
  table(
    searched(rows),
    [
      ["Report", (r) => r.id],
      ["Kind", (r) => r.kind],
      ["Source / denominator origin", (r) => r.source],
    ],
    (row) => {
      details(row.id, row.value);
      message(
        `Source: ${row.source}. Metrics must be interpreted within this report's explicit denominator.`,
      );
    },
  );
}
function renderBody() {
  $("visual").replaceChildren();
  $("listing").replaceChildren();
  ({
    graph: graphBody,
    run: runBody,
    content: contentBody,
    quality: qualityBody,
  })[state.view]();
}
function setHash() {
  const values = new URLSearchParams({ view: state.view, graph: state.graph });
  if (state.selected) values.set("selected", state.selected);
  history.replaceState(null, "", `#${values}`);
}
function render() {
  $("controls").replaceChildren();
  document
    .querySelectorAll("nav button")
    .forEach((node) =>
      node.classList.toggle("active", node.dataset.view === state.view),
    );
  ({
    graph: graphControls,
    run: runControls,
    content: contentControls,
    quality: qualityControls,
  })[state.view]();
  renderBody();
  setHash();
}
for (const node of document.querySelectorAll("nav button"))
  node.addEventListener("click", () => {
    state.view = node.dataset.view;
    state.page = 0;
    state.query = "";
    render();
  });
$("identity").textContent =
  `Run ${D.run_id}  |  ${D.graphs.length} graph snapshots  |  ${D.stages.length} stage records  |  ${D.events.length} events`;
$("capture").textContent =
  `Captured ${D.capture.finished}. ${D.diagnostics.length} diagnostics. Redactions: ${D.capture.redactions.fields} fields / ${D.capture.redactions.strings} strings. Local project content; keep this export private.`;
const fragment = new URLSearchParams(location.hash.slice(1));
if (["graph", "run", "content", "quality"].includes(fragment.get("view")))
  state.view = fragment.get("view");
if (D.graphs.some((item) => item.id === fragment.get("graph")))
  state.graph = fragment.get("graph");
state.selected = fragment.get("selected");
render();
if (state.selected) selectNode(state.selected);
else
  details("Run identity and capture", {
    run_id: D.run_id,
    capture: D.capture,
    manifest: D.run_manifest,
  });
