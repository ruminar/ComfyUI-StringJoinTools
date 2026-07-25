import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const TARGET_NODE = "StringJoinTools_RuntimeToggleJoin10";
const LIVE_ROUTE = "/string_join_tools/runtime_state";

function widgetByName(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function hideSavedWidget(widget) {
    if (!widget || widget.__stringJoinToolsHidden) return;
    widget.__stringJoinToolsHidden = true;
    widget.computeSize = () => [0, -4];
    widget.draw = () => {};
}

function randomStateKey() {
    if (globalThis.crypto?.randomUUID) {
        return `sjt-${globalThis.crypto.randomUUID()}`;
    }
    return `sjt-${Date.now().toString(36)}-${Math.random()
        .toString(36)
        .slice(2)}`;
}

function inputIndexes(node) {
    return (node.inputs ?? [])
        .map((input) => {
            const match = /^text_(\d+)$/.exec(input.name ?? "");
            return match ? Number(match[1]) - 1 : null;
        })
        .filter((index) => Number.isInteger(index))
        .sort((a, b) => a - b);
}

function readState(node) {
    const indexes = inputIndexes(node);
    const inputCount = indexes.length;
    const maxMask = inputCount > 0 ? (1 << inputCount) - 1 : 0;

    const modeWidget = widgetByName(node, "mode");
    const maskWidget = widgetByName(node, "enabled_mask");
    const selectedWidget = widgetByName(node, "selected_index");
    const keyWidget = widgetByName(node, "state_key");

    const mode = modeWidget?.value === "single" ? "single" : "multiple";
    let enabledMask = Number(maskWidget?.value ?? maxMask) & maxMask;
    let selectedIndex = Number(selectedWidget?.value ?? -1);

    if (
        !Number.isInteger(selectedIndex) ||
        selectedIndex < 0 ||
        selectedIndex >= inputCount
    ) {
        selectedIndex = -1;
    }

    if (mode === "single") {
        if (enabledMask === 0) {
            selectedIndex = -1;
        } else {
            if (
                selectedIndex < 0 ||
                (enabledMask & (1 << selectedIndex)) === 0
            ) {
                selectedIndex =
                    indexes.find((index) => enabledMask & (1 << index)) ?? -1;
            }
            enabledMask = selectedIndex >= 0 ? 1 << selectedIndex : 0;
        }
    }

    return {
        stateKey: String(keyWidget?.value ?? "").trim(),
        mode,
        enabledMask,
        selectedIndex,
        inputCount,
    };
}

function writeStateWidgets(node, state) {
    const maskWidget = widgetByName(node, "enabled_mask");
    const selectedWidget = widgetByName(node, "selected_index");
    const modeWidget = widgetByName(node, "mode");

    if (maskWidget) maskWidget.value = state.enabledMask;
    if (selectedWidget) selectedWidget.value = state.selectedIndex;
    if (modeWidget && modeWidget.value !== state.mode) {
        modeWidget.value = state.mode;
    }
}

function ensureStateKey(node) {
    const keyWidget = widgetByName(node, "state_key");
    if (!keyWidget) return "";

    let key = String(keyWidget.value ?? "").trim();
    const duplicate = () =>
        (app.graph?._nodes ?? []).some(
            (other) =>
                other !== node &&
                other.comfyClass === node.comfyClass &&
                String(widgetByName(other, "state_key")?.value ?? "").trim() === key,
        );

    if (!key || duplicate()) {
        key = randomStateKey();
        keyWidget.value = key;
    }
    return key;
}

function markWorkflowChanged(node) {
    node.setDirtyCanvas?.(true, true);
    node.graph?.setDirtyCanvas?.(true, true);
    node.graph?.change?.();
    app.canvas?.setDirty?.(true, true);
}

function applyButtonAppearance(button, enabled, index) {
    button.textContent = `${index + 1} ${enabled ? "ON" : "OFF"}`;
    button.title = `text_${index + 1}: ${enabled ? "enabled" : "disabled"}`;
    button.style.border = enabled
        ? "1px solid rgba(100, 255, 150, 0.85)"
        : "1px solid rgba(255, 255, 255, 0.16)";
    button.style.background = enabled
        ? "rgba(31, 145, 79, 0.88)"
        : "rgba(40, 40, 40, 0.72)";
    button.style.color = enabled ? "#ffffff" : "rgba(255,255,255,0.72)";
    button.style.boxShadow = enabled
        ? "inset 0 1px 2px rgba(0,0,0,0.42)"
        : "none";
}

function renderControls(node) {
    const ui = node.__stringJoinToolsRuntimeUI;
    if (!ui) return;

    const state = readState(node);
    writeStateWidgets(node, state);

    ui.buttons.forEach((button, index) => {
        applyButtonAppearance(
            button,
            Boolean(state.enabledMask & (1 << index)),
            index,
        );
    });

    ui.modeLabel.textContent =
        state.mode === "single"
            ? "Single mode · 0 or 1 input"
            : "Multiple mode · independent inputs";
}

async function syncRuntimeState(node, reason = "update") {
    const ui = node.__stringJoinToolsRuntimeUI;
    const stateKey = ensureStateKey(node);
    const state = readState(node);
    state.stateKey = stateKey;

    writeStateWidgets(node, state);
    renderControls(node);

    if (ui) {
        ui.status.textContent = `Syncing live state (${reason})…`;
        ui.status.style.color = "";
    }

    try {
        const response = await api.fetchApi(LIVE_ROUTE, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                state_key: state.stateKey,
                mode: state.mode,
                enabled_mask: state.enabledMask,
                selected_index: state.selectedIndex,
                input_count: state.inputCount,
            }),
        });

        if (!response.ok) {
            const details = await response.text();
            throw new Error(`${response.status}: ${details}`);
        }

        const payload = await response.json();
        if (ui) {
            const revision = payload?.state?.revision;
            ui.status.textContent =
                revision == null
                    ? "Live state synced"
                    : `Live state synced · revision ${revision}`;
            ui.status.style.color = "rgba(165,255,195,0.9)";
        }
    } catch (error) {
        console.error("[StringJoinTools] Live state sync failed", error);
        if (ui) {
            ui.status.textContent =
                "Live sync failed · queued saved state will be used";
            ui.status.style.color = "rgba(255,170,150,0.95)";
        }
    }
}

function toggleInput(node, index) {
    const state = readState(node);
    const bit = 1 << index;

    if (state.mode === "single") {
        if (state.enabledMask & bit) {
            state.enabledMask = 0;
            state.selectedIndex = -1;
        } else {
            state.enabledMask = bit;
            state.selectedIndex = index;
        }
    } else {
        state.enabledMask ^= bit;
        if (state.enabledMask & bit) {
            state.selectedIndex = index;
        } else if (state.selectedIndex === index) {
            state.selectedIndex =
                inputIndexes(node).find(
                    (candidate) => state.enabledMask & (1 << candidate),
                ) ?? -1;
        }
    }

    writeStateWidgets(node, state);
    renderControls(node);
    markWorkflowChanged(node);
    void syncRuntimeState(node, `toggle ${index + 1}`);
}

function normaliseAfterModeChange(node) {
    const state = readState(node);
    writeStateWidgets(node, state);
    renderControls(node);
    markWorkflowChanged(node);
    void syncRuntimeState(node, `mode ${state.mode}`);
}

function buildRuntimeControls(node) {
    if (node.__stringJoinToolsRuntimeUI) return;

    const indexes = inputIndexes(node);
    if (indexes.length === 0) return;

    const root = document.createElement("div");
    root.style.display = "flex";
    root.style.flexDirection = "column";
    root.style.gap = "5px";
    root.style.width = "100%";
    root.style.boxSizing = "border-box";
    root.style.padding = "2px 0";

    const modeLabel = document.createElement("div");
    modeLabel.style.fontSize = "11px";
    modeLabel.style.opacity = "0.72";
    modeLabel.style.padding = "0 2px";

    const grid = document.createElement("div");
    grid.style.display = "grid";
    grid.style.gridTemplateColumns = "repeat(5, minmax(0, 1fr))";
    grid.style.gap = "4px";

    const buttons = indexes.map((index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.style.minWidth = "0";
        button.style.height = "25px";
        button.style.padding = "2px 4px";
        button.style.borderRadius = "4px";
        button.style.cursor = "pointer";
        button.style.fontSize = "11px";
        button.style.fontWeight = "600";
        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            toggleInput(node, index);
        });
        grid.appendChild(button);
        return button;
    });

    const status = document.createElement("div");
    status.textContent = "Live state not synced yet";
    status.style.fontSize = "10px";
    status.style.opacity = "0.78";
    status.style.padding = "0 2px";

    root.append(modeLabel, grid, status);

    const domWidget = node.addDOMWidget(
        "runtime_toggle_controls",
        "string-join-tools-runtime-controls",
        root,
        {
            serialize: false,
            hideOnZoom: false,
        },
    );
    domWidget.computeSize = (width) => [width, 72];

    node.__stringJoinToolsRuntimeUI = {
        root,
        modeLabel,
        buttons,
        status,
        domWidget,
    };

    const modeWidget = widgetByName(node, "mode");
    if (modeWidget && !modeWidget.__stringJoinToolsWrapped) {
        modeWidget.__stringJoinToolsWrapped = true;
        const originalCallback = modeWidget.callback;
        modeWidget.callback = function (value, ...args) {
            const result = originalCallback?.call(this, value, ...args);
            queueMicrotask(() => normaliseAfterModeChange(node));
            return result;
        };
    }

    hideSavedWidget(widgetByName(node, "enabled_mask"));
    hideSavedWidget(widgetByName(node, "selected_index"));
    hideSavedWidget(widgetByName(node, "state_key"));

    ensureStateKey(node);
    renderControls(node);

    const width = Math.max(node.size?.[0] ?? 0, 360);
    const height = Math.max(node.size?.[1] ?? 0, node.computeSize?.()[1] ?? 0);
    node.setSize?.([width, height]);
}

function initialiseRuntimeNode(node, reason) {
    buildRuntimeControls(node);
    ensureStateKey(node);
    renderControls(node);
    void syncRuntimeState(node, reason);
}

app.registerExtension({
    name: "ruminar.StringJoinTools.RuntimeToggleJoin",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== TARGET_NODE) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalOnNodeCreated?.apply(this, arguments);
            setTimeout(() => initialiseRuntimeNode(this, "node created"), 0);
            return result;
        };

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const result = originalOnConfigure?.apply(this, arguments);
            setTimeout(() => initialiseRuntimeNode(this, "workflow loaded"), 0);
            return result;
        };
    },
});
