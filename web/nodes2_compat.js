import { app } from "../../scripts/app.js";

const adapters = new Map();
let observer = null;
let refreshScheduled = false;

function nodeForElement(element) {
    const rawId = element.dataset.nodeId;
    if (rawId == null) return null;

    const numericId = Number(rawId);
    const ids = Number.isFinite(numericId) ? [rawId, numericId] : [rawId];
    const graphs = [app.canvas?.graph, app.graph].filter(
        (graph, index, values) => graph && values.indexOf(graph) === index,
    );

    for (const graph of graphs) {
        for (const id of ids) {
            const node = graph.getNodeById?.(id);
            if (node) return node;
        }
    }
    return null;
}

function applyAdapters() {
    refreshScheduled = false;
    for (const element of document.querySelectorAll(".lg-node[data-node-id]")) {
        const node = nodeForElement(element);
        if (!node) continue;

        const adapter = adapters.get(node.comfyClass ?? node.type);
        if (adapter) adapter(node, element);
    }
}

function scheduleRefresh() {
    if (refreshScheduled) return;
    refreshScheduled = true;
    requestAnimationFrame(applyAdapters);
}

function ensureObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(scheduleRefresh);
    observer.observe(document.body, { childList: true, subtree: true });
}

export function registerNodes2Adapter(nodeNames, adapter) {
    for (const nodeName of nodeNames) adapters.set(nodeName, adapter);
    ensureObserver();
    scheduleRefresh();
}

export function refreshNodes2Node(node) {
    ensureObserver();
    for (const element of document.querySelectorAll(".lg-node[data-node-id]")) {
        if (nodeForElement(element) === node) {
            const adapter = adapters.get(node.comfyClass ?? node.type);
            adapter?.(node, element);
            return;
        }
    }
    scheduleRefresh();
}

export function setNodes2RuntimeTint(element, enabled) {
    if (enabled) {
        element.dataset.stringJoinToolsRuntime = "true";
    } else {
        delete element.dataset.stringJoinToolsRuntime;
    }
}

const style = document.createElement("style");
style.textContent = `
.lg-node[data-string-join-tools-runtime="true"] [data-testid^="node-body-"] {
    position: relative;
}

.lg-node[data-string-join-tools-runtime="true"] [data-testid^="node-body-"]::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 1;
    border-radius: inherit;
    background: rgba(255, 210, 70, 0.1);
    pointer-events: none;
}

.string-join-tools-nodes2-row-click:hover {
    background: rgba(255, 255, 255, 0.1);
}

.string-join-tools-nodes2-row >
    :not(.string-join-tools-nodes2-row-visual):not(.string-join-tools-nodes2-row-click) {
    z-index: 2;
}
`;
document.head.appendChild(style);
