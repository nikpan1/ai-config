"use strict";
const topologyLayouts = new Map();
function topologyLayout(nodes, edges, key) {
  if (topologyLayouts.has(key)) return topologyLayouts.get(key);
  const byId = new Map(nodes.map((node) => [node.id, { ...node, links: [] }]));
  for (const edge of edges) {
    byId.get(edge.source_id)?.links.push(edge.target_id);
    byId.get(edge.target_id)?.links.push(edge.source_id);
  }
  const unseen = new Set(byId.keys()), groups = [];
  while (unseen.size) {
    const queue = [unseen.values().next().value], group = [];
    unseen.delete(queue[0]);
    while (queue.length) {
      const node = byId.get(queue.pop());
      group.push(node);
      for (const id of node.links) if (unseen.delete(id)) queue.push(id);
    }
    groups.push(group);
  }
  groups.sort((a, b) => b.length - a.length);
  const positions = new Map();
  let left = 0, top = 0, rowHeight = 0;
  const rowWidth = Math.max(1100, Math.sqrt(nodes.length) * 125);
  for (const group of groups) {
    const count = group.length, radius = Math.max(65, Math.sqrt(count) * 45);
    group.forEach((node, i) => {
      node.x = Math.cos(i * 2.39996) * radius * Math.sqrt((i + 1) / count);
      node.y = Math.sin(i * 2.39996) * radius * Math.sqrt((i + 1) / count);
    });
    const ids = new Set(group.map((node) => node.id));
    const localEdges = edges.filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id));
    const iterations = Math.max(8, Math.min(180, Math.floor(6000000 / (count * count))));
    for (let step = 0; step < iterations; step++) {
      for (const node of group) { node.dx = -node.x * 0.006; node.dy = -node.y * 0.006; }
      for (let i = 0; i < count; i++) for (let j = i + 1; j < count; j++) {
        const a = group[i], b = group[j], x = a.x - b.x, y = a.y - b.y;
        const distance = Math.max(1, Math.hypot(x, y)), force = 1600 / (distance * distance);
        a.dx += x * force; a.dy += y * force;
        b.dx -= x * force; b.dy -= y * force;
      }
      for (const edge of localEdges) {
        const a = byId.get(edge.source_id), b = byId.get(edge.target_id);
        const x = b.x - a.x, y = b.y - a.y, distance = Math.max(1, Math.hypot(x, y));
        const force = (distance - 125) * 0.035 / distance;
        a.dx += x * force; a.dy += y * force;
        b.dx -= x * force; b.dy -= y * force;
      }
      const limit = 14 * (1 - step / iterations) + 1;
      for (const node of group) {
        node.x += Math.max(-limit, Math.min(limit, node.dx));
        node.y += Math.max(-limit, Math.min(limit, node.dy));
      }
    }
    const minX = Math.min(...group.map((n) => n.x)), minY = Math.min(...group.map((n) => n.y));
    const width = Math.max(...group.map((n) => n.x)) - minX + 180;
    const height = Math.max(...group.map((n) => n.y)) - minY + 150;
    if (left && left + width > rowWidth) { left = 0; top += rowHeight; rowHeight = 0; }
    for (const node of group) positions.set(node.id, { x: left + node.x - minX + 70, y: top + node.y - minY + 60 });
    left += width; rowHeight = Math.max(rowHeight, height);
  }
  const layout = { positions, camera: null };
  topologyLayouts.set(key, layout);
  return layout;
}
function createTopology(parent, options) {
  const { nodes, edges, label, onSelect, onEdge, key } = options;
  const toolbar = el("div", undefined, parent, "topology-toolbar");
  const frame = el("div", undefined, parent, "topology-frame");
  const svgNS = "http://www.w3.org/2000/svg";
  const make = (tag, attributes, owner) => {
    const node = document.createElementNS(svgNS, tag);
    for (const [name, value] of Object.entries(attributes || {})) node.setAttribute(name, value);
    owner?.append(node);
    return node;
  };
  const svg = make("svg", { class: "topology-canvas", viewBox: "0 0 1100 680", "aria-label": "Interactive directed knowledge graph", tabindex: "0" }, frame);
  const defs = make("defs", {}, svg);
  const marker = make("marker", { id: "topology-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
  make("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#8ba4bc" }, marker);
  const world = make("g", {}, svg), edgeLayer = make("g", {}, world), nodeLayer = make("g", {}, world);
  const layout = topologyLayout(nodes, edges, key), positions = layout.positions;
  let selected = options.selected, camera = layout.camera || { x: 0, y: 0, scale: 1 }, drag = null;
  const types = [...new Set(nodes.map((node) => node.type))].sort();
  const colors = new Map(types.map((type, index) => [type, palette[index % palette.length]]));
  const edgeElements = [], nodeElements = new Map();
  const labelToggle = el("label", undefined, toolbar, "topology-toggle");
  const allLabels = el("input", undefined, labelToggle);
  allLabels.type = "checkbox";
  el("span", "All labels", labelToggle);
  const zoomText = el("span", undefined, toolbar, "hint");
  const point = (event) => {
    const p = svg.createSVGPoint(); p.x = event.clientX; p.y = event.clientY;
    return p.matrixTransform(svg.getScreenCTM().inverse());
  };
  const applyCamera = () => {
    world.setAttribute("transform", `translate(${camera.x} ${camera.y}) scale(${camera.scale})`);
    layout.camera = { ...camera };
    zoomText.textContent = `${Math.round(camera.scale * 100)}%`;
    svg.classList.toggle("show-labels", allLabels.checked || camera.scale >= 0.95);
  };
  const zoom = (factor, point = { x: 550, y: 340 }) => {
    const scale = Math.max(0.04, Math.min(8, camera.scale * factor));
    camera.x = point.x - (point.x - camera.x) * scale / camera.scale;
    camera.y = point.y - (point.y - camera.y) * scale / camera.scale;
    camera.scale = scale; applyCamera();
  };
  const fit = () => {
    const points = nodes.map((node) => positions.get(node.id));
    if (!points.length) return;
    const minX = Math.min(...points.map((p) => p.x)) - 65, minY = Math.min(...points.map((p) => p.y)) - 55;
    const width = Math.max(...points.map((p) => p.x)) - minX + 100;
    const height = Math.max(...points.map((p) => p.y)) - minY + 65;
    const scale = Math.min(1020 / width, 600 / height, 2);
    camera = { x: (1100 - width * scale) / 2 - minX * scale, y: (680 - height * scale) / 2 - minY * scale, scale };
    applyCamera();
  };
  button("Fit graph", fit, toolbar);
  button("Zoom in", () => zoom(1.35), toolbar);
  button("Zoom out", () => zoom(1 / 1.35), toolbar);
  button("Center selected", () => {
    const p = positions.get(selected);
    if (p) { camera = { x: 550 - p.x * 1.5, y: 340 - p.y * 1.5, scale: 1.5 }; applyCamera(); }
  }, toolbar);
  const closeExpanded = button("Close expanded canvas", () => frame.classList.remove("expanded"), frame);
  closeExpanded.className = "topology-close";
  button("Expand canvas", () => { frame.classList.toggle("expanded"); svg.focus(); }, toolbar);
  allLabels.addEventListener("change", applyCamera);
  const pairs = new Map();
  for (const edge of edges) {
    const pair = [edge.source_id, edge.target_id].sort().join("|");
    if (!pairs.has(pair)) pairs.set(pair, []);
    pairs.get(pair).push(edge);
  }
  for (const edge of edges) {
    const group = make("g", { class: "topology-edge", tabindex: "0", role: "button", "aria-label": `${label(edge.source_id)} ${edge.type} ${label(edge.target_id)}` }, edgeLayer);
    const path = make("path", { "marker-end": "url(#topology-arrow)" }, group);
    if (edge.status === "uncertain" || edge.status === "inferred") path.setAttribute("stroke-dasharray", "6 4");
    const hit = make("path", { class: "edge-hit" }, group);
    const text = make("text", { class: "edge-label", "text-anchor": "middle" }, group); text.textContent = edge.type;
    make("title", {}, group).textContent = `${edge.type}: ${label(edge.source_id)} -> ${label(edge.target_id)}\n${edge.description || edge.method || "Method not recorded"}\n${edge.status || ""}`;
    const activate = () => onEdge(edge);
    group.addEventListener("click", activate);
    group.addEventListener("keydown", (event) => { if (event.key === "Enter") activate(); });
    edgeElements.push({ edge, group, path, hit, text });
  }
  for (const node of nodes) {
    const group = make("g", { class: "topology-node", "data-node-id": node.id, tabindex: "0", role: "button", "aria-label": label(node.id) }, nodeLayer);
    make(node.type === "Assertion" ? "rect" : "circle", node.type === "Assertion" ? { x: -12, y: -12, width: 24, height: 24, rx: 5, fill: colors.get(node.type) } : { r: node.type === "SourceSpan" ? 7 : 9, fill: colors.get(node.type) }, group);
    const text = make("text", { x: 16, y: 4, class: "node-label" }, group);
    const name = label(node.id); text.textContent = name.length > 52 ? name.slice(0, 49) + "..." : name;
    make("title", {}, group).textContent = `${node.type}\n${name}\n${node.id}`;
    group.addEventListener("keydown", (event) => { if (event.key === "Enter") onSelect(node.id); });
    nodeElements.set(node.id, group);
  }
  const paint = () => {
    for (const [id, group] of nodeElements) { const p = positions.get(id); group.setAttribute("transform", `translate(${p.x} ${p.y})`); }
    for (const item of edgeElements) {
      const { edge } = item, a = positions.get(edge.source_id), b = positions.get(edge.target_id);
      const siblings = pairs.get([edge.source_id, edge.target_id].sort().join("|"));
      const bend = (siblings.indexOf(edge) - (siblings.length - 1) / 2) * 36;
      const dx = b.x - a.x, dy = b.y - a.y, length = Math.max(1, Math.hypot(dx, dy));
      const direction = edge.source_id < edge.target_id ? 1 : -1;
      const cx = (a.x + b.x) / 2 - dy / length * bend * direction;
      const cy = (a.y + b.y) / 2 + dx / length * bend * direction;
      const endLength = Math.max(1, Math.hypot(b.x - cx, b.y - cy));
      const endX = b.x - (b.x - cx) / endLength * 16, endY = b.y - (b.y - cy) / endLength * 16;
      const loop = edge.source_id === edge.target_id;
      const d = loop ? `M ${a.x - 8} ${a.y - 8} C ${a.x - 65} ${a.y - 80} ${a.x + 65} ${a.y - 80} ${a.x + 10} ${a.y - 10}` : `M ${a.x} ${a.y} Q ${cx} ${cy} ${endX} ${endY}`;
      item.path.setAttribute("d", d); item.hit.setAttribute("d", d);
      item.text.setAttribute("x", loop ? a.x : (a.x + 2 * cx + b.x) / 4);
      item.text.setAttribute("y", loop ? a.y - 58 : (a.y + 2 * cy + b.y) / 4 - 5);
    }
  };
  const selectNode = (id) => {
    id = nodeElements.has(id) ? id : null;
    selected = id;
    const adjacent = new Set([id]);
    for (const { edge, group } of edgeElements) {
      const active = edge.source_id === id || edge.target_id === id;
      group.classList.toggle("related", active);
      group.classList.toggle("muted", Boolean(id) && !active);
      if (active) { adjacent.add(edge.source_id); adjacent.add(edge.target_id); }
    }
    for (const [key, group] of nodeElements) {
      group.classList.toggle("selected", key === id);
      group.classList.toggle("related", adjacent.has(key));
      group.classList.toggle("muted", Boolean(id) && !adjacent.has(key));
    }
  };
  svg.addEventListener("wheel", (event) => { event.preventDefault(); zoom(Math.exp(-event.deltaY * 0.0015), point(event)); }, { passive: false });
  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.target.closest(".topology-edge")) return;
    const p = point(event), id = event.target.closest("[data-node-id]")?.getAttribute("data-node-id");
    drag = { id, start: p, last: p, moved: false };
    svg.setPointerCapture(event.pointerId);
  });
  svg.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const p = point(event), dx = p.x - drag.last.x, dy = p.y - drag.last.y;
    if (Math.hypot(p.x - drag.start.x, p.y - drag.start.y) > 4) drag.moved = true;
    if (drag.id) { const node = positions.get(drag.id); node.x += dx / camera.scale; node.y += dy / camera.scale; paint(); }
    else { camera.x += dx; camera.y += dy; applyCamera(); }
    drag.last = p;
  });
  svg.addEventListener("pointerup", (event) => {
    if (!drag) return;
    const { id, moved } = drag; drag = null;
    svg.releasePointerCapture(event.pointerId);
    if (id && !moved) onSelect(id);
  });
  svg.addEventListener("pointercancel", () => { drag = null; });
  svg.addEventListener("keydown", (event) => {
    if (event.key === "Escape") frame.classList.remove("expanded");
    else if (event.key === "+" || event.key === "=") zoom(1.35);
    else if (event.key === "-") zoom(1 / 1.35);
    else if (event.key === "0") fit();
    else return;
    event.preventDefault();
  });
  const legend = el("div", undefined, parent, "topology-legend");
  for (const type of types) {
    const item = el("span", `${type}: ${nodes.filter((n) => n.type === type).length}`, legend);
    item.style.color = colors.get(type);
  }
  message(`${nodes.length} nodes / ${edges.length} directed edges. Scroll to zoom; drag background to pan; drag nodes to rearrange; click a node or edge for evidence. Separate clusters are disconnected components. Layout distance does not imply semantic similarity.`, parent);
  paint(); selectNode(selected);
  if (layout.camera) applyCamera(); else fit();
  return { select: selectNode };
}
