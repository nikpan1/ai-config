"use strict";
const data = JSON.parse(document.getElementById("graph-data").textContent);
const graph = data.graph;
const colors = { capability: "#168a75", business_scenario: "#bb4c75", actor: "#d7a32a", process: "#4f8fc3", customer_input: "#c57149", prerequisite: "#8561a8", integration: "#507468", configuration: "#8b9547", constraint: "#a34c4e" };
const claims = new Map(graph.claims.map(c => [c.id, c]));
const spans = new Map(data.spans.map(s => [s.id, s]));
const evidence = new Map(graph.evidence.map(e => [e.id, e]));
const assets = new Map(data.assets.map(a => [a.id, a]));
const nodes = new vis.DataSet();
const edges = new vis.DataSet();
const network = new vis.Network(document.getElementById("network"), {nodes, edges}, {
  nodes: {shape: "dot", size: 15, font: {size: 13, color: "#25272c", multi: false}},
  edges: {color: "#aab4bf", font: {size: 11, color: "#626773"}, smooth: false},
  physics: {stabilization: {iterations: 180}, barnesHut: {gravitationalConstant: -5000}},
  interaction: {hover: true, navigationButtons: false, keyboard: true}
});
let expanded = null;
function element(tag, text, parent, className) {
  const el = document.createElement(tag); el.textContent = text;
  if (className) el.className = className;
  if (parent) parent.appendChild(el);
  return el;
}
for (const [type, color] of Object.entries(colors)) {
  const label = element("span", "", document.getElementById("legend"), "legend-item");
  const swatch = element("span", "", label, "swatch"); swatch.style.background = color;
  element("span", type.replaceAll("_", " "), label);
}
for (const entity of graph.entities.filter(e => e.type === "capability")) {
  const option = element("option", entity.name, document.getElementById("capability")); option.value = entity.id;
}
function draw() {
  const query = document.getElementById("search").value.toLowerCase();
  const status = document.getElementById("status").value;
  const capability = document.getElementById("capability").value || expanded;
  let selected = graph.entities.filter(e => (!query || [e.name, ...e.aliases].some(n => n.toLowerCase().includes(query))) &&
    (!status || graph.claims.some(c => c.entity_ids.includes(e.id) && c.status === status)));
  if (capability) {
    const neighbors = new Set([capability]);
    graph.relationships.forEach(r => { if (r.subject === capability || r.object === capability) { neighbors.add(r.subject); neighbors.add(r.object); } });
    selected = selected.filter(e => neighbors.has(e.id));
  } else if (!query && !status) {
    const capabilities = selected.filter(e => e.type === "capability");
    selected = capabilities.length ? capabilities : selected;
  }
  selected = selected.slice(0, 120);
  const ids = new Set(selected.map(e => e.id));
  nodes.clear(); edges.clear();
  nodes.add(selected.map(e => ({id: e.id, label: e.name.length > 45 ? e.name.slice(0, 42) + "..." : e.name, color: colors[e.type]})));
  edges.add(graph.relationships.filter(r => ids.has(r.subject) && ids.has(r.object) && (!status || r.claim_ids.some(id => claims.get(id)?.status === status)))
    .map(r => ({id: r.id, from: r.subject, to: r.object, label: r.type.replaceAll("_", " "), arrows: r.direction === "directed" ? "to" : ""})));
  document.getElementById("counts").textContent = `${nodes.length} of ${graph.entities.length} entities · ${graph.claims.length} claims`;
  document.getElementById("empty").hidden = nodes.length > 0;
  network.fit({animation: false});
}
function showEvidence(id, parent) {
  const ev = evidence.get(id); if (!ev) return;
  const details = document.createElement("details"); parent.appendChild(details);
  element("summary", id, details);
  const span = spans.get(ev.span_id);
  if (span) {
    element("p", `${span.path}:${span.start_line}-${span.end_line}`, details);
    element("pre", (span.table_header_excerpt || "") + span.excerpt, details);
  }
  if (ev.kind === "reviewer") element("p", `${ev.reviewer}: ${ev.statement}`, details);
  const asset = assets.get(ev.asset_id);
  if (asset?.local) { const img = document.createElement("img"); img.src = asset.local; img.alt = asset.alt; details.appendChild(img); }
}
function showSelection(entityId, edgeId) {
  const panel = document.getElementById("details"); panel.replaceChildren();
  const entity = graph.entities.find(e => e.id === entityId);
  const edge = graph.relationships.find(e => e.id === edgeId);
  element("h2", entity ? entity.name : edge?.type.replaceAll("_", " ") || "Evidence", panel);
  if (entity) element("p", [entity.type.replaceAll("_", " "), entity.scope, entity.version].filter(Boolean).join(" · "), panel);
  const relevant = entity ? graph.claims.filter(c => c.entity_ids.includes(entity.id)) : (edge?.claim_ids || []).map(id => claims.get(id)).filter(Boolean);
  relevant.forEach(claim => {
    const article = element("article", "", panel);
    element("span", claim.status, article, "status");
    element("p", claim.assertion, article);
    if (claim.conditions.length) element("p", "Conditions: " + claim.conditions.join("; "), article);
    if (claim.exceptions.length) element("p", "Exceptions: " + claim.exceptions.join("; "), article);
    graph.conflicts.filter(c => c.claim_ids.includes(claim.id)).forEach(c => element("p", `Conflict (${c.status}): ${c.description}`, article));
    claim.evidence_ids.forEach(id => showEvidence(id, article));
  });
}
network.on("click", event => {
  if (event.nodes.length) showSelection(event.nodes[0], null);
  else if (event.edges.length) showSelection(null, event.edges[0]);
});
network.on("doubleClick", event => { if (event.nodes.length) { expanded = event.nodes[0]; draw(); } });
for (const id of ["search", "capability", "status"]) document.getElementById(id).addEventListener("input", draw);
document.getElementById("fit").onclick = () => network.fit({animation: true});
document.getElementById("reset").onclick = () => {
  expanded = null; ["search", "capability", "status"].forEach(id => document.getElementById(id).value = ""); draw();
};
draw();
