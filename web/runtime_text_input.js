import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const TARGET_NODE = "StringJoinTools_RuntimeTextInput";
const LIVE_ROUTE = "/string_join_tools/runtime_text_state";
const DEBOUNCE_MS = 120;
const MAX_TEXT_BYTES = 512 * 1024;
const LIVE_BACKGROUND_TINT = "rgba(255, 210, 70, 0.1)";

function widgetByName(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}

function hideSavedWidget(widget) {
    if (!widget) return;

    if (!widget.__stringJoinToolsHidden) {
        widget.__stringJoinToolsHidden = true;
        widget.type = "hidden";
        widget.hidden = true;
        widget.disabled = true;
        widget.serialize = true;
        widget.options = { ...(widget.options ?? {}), hidden: true };
        widget.computeSize = () => [0, -4];
        widget.draw = () => {};
    }

    // Recent ComfyUI versions render multiline STRING widgets as DOM
    // elements. Suppressing only the LiteGraph draw function leaves that
    // textarea visible underneath our live editor.
    const elements = new Set([
        widget.element,
        widget.inputEl,
        widget.domWidget?.element,
        widget.options?.element,
    ]);
    for (const element of elements) {
        if (!(element instanceof HTMLElement)) continue;
        element.hidden = true;
        element.setAttribute("aria-hidden", "true");
        element.style.setProperty("display", "none", "important");
        element.style.setProperty("visibility", "hidden", "important");
        element.style.setProperty("pointer-events", "none", "important");
    }
}

function randomId(prefix) {
    if (globalThis.crypto?.randomUUID) {
        return `${prefix}-${globalThis.crypto.randomUUID()}`;
    }
    return `${prefix}-${Date.now().toString(36)}-${Math.random()
        .toString(36)
        .slice(2)}`;
}

function nodeClass(node) {
    return node.comfyClass ?? node.type;
}

function ensureUniqueStateKey(node) {
    const keyWidget = widgetByName(node, "state_key");
    if (!keyWidget) return "";

    let key =
        typeof keyWidget.value === "string" ? keyWidget.value.trim() : "";
    const duplicate = (app.graph?._nodes ?? []).some(
        (other) => {
            const otherKey = widgetByName(other, "state_key")?.value;
            return (
                other !== node &&
                nodeClass(other) === TARGET_NODE &&
                typeof otherKey === "string" &&
                otherKey.trim() === key
            );
        },
    );
    if (!key || duplicate) {
        key = randomId("sjt-text");
        keyWidget.value = key;
        node.graph?.change?.();
    }
    return key;
}

function characterCount(value) {
    return Array.from(value).length;
}

function utf8ByteCount(value) {
    return new TextEncoder().encode(value).length;
}

function markWorkflowChanged(node) {
    node.graph?.change?.();
    node.setDirtyCanvas?.(true, false);
}

function setStatus(node, status, detail = "") {
    const ui = node.__stringJoinToolsRuntimeTextUI;
    if (!ui) return;
    ui.status.textContent = detail ? `${status} · ${detail}` : status;
    ui.status.dataset.state = status;
    ui.status.style.color =
        status === "SYNC ERROR"
            ? "rgba(255,155,135,0.98)"
            : status === "LIVE"
              ? "rgba(165,255,195,0.95)"
              : status === "SYNCING"
                ? "rgba(255,220,135,0.95)"
                : "rgba(215,215,225,0.9)";
}

function renderCount(node, value) {
    const ui = node.__stringJoinToolsRuntimeTextUI;
    if (!ui) return;
    const bytes = utf8ByteCount(value);
    ui.count.textContent =
        bytes > MAX_TEXT_BYTES
            ? `${characterCount(value)} characters · ${bytes} / ${MAX_TEXT_BYTES} bytes`
            : `${characterCount(value)} characters`;
    ui.count.style.color =
        bytes > MAX_TEXT_BYTES
            ? "rgba(255,155,135,0.98)"
            : "rgba(210,210,220,0.72)";
}

function setLocalText(node, value, { sync = false, dirty = false } = {}) {
    const text = typeof value === "string" ? value : String(value ?? "");
    const textWidget = widgetByName(node, "text");
    const ui = node.__stringJoinToolsRuntimeTextUI;
    const savedValueChanged = Boolean(
        textWidget && textWidget.value !== text,
    );
    if (savedValueChanged) textWidget.value = text;
    if (ui && ui.textarea.value !== text) ui.textarea.value = text;
    renderCount(node, text);
    if (dirty && savedValueChanged) markWorkflowChanged(node);
    if (sync) scheduleSync(node, text);
    return text;
}

function scheduleSync(node, value, immediate = false) {
    const sync = node.__stringJoinToolsRuntimeTextSync;
    if (!sync) return;
    sync.desiredText = value;
    clearTimeout(sync.timer);
    if (!sync.inFlight && sync.acknowledgedText === value) {
        sync.timer = null;
        setStatus(
            node,
            "LIVE",
            sync.revision == null
                ? "server accepted"
                : `revision ${sync.revision}`,
        );
        return;
    }
    setStatus(node, "EDITING");
    sync.timer = setTimeout(
        () => void flushSync(node),
        immediate ? 0 : DEBOUNCE_MS,
    );
}

async function responseError(response) {
    try {
        const payload = await response.json();
        return payload?.error ?? `${response.status} ${response.statusText}`;
    } catch {
        return `${response.status} ${response.statusText}`;
    }
}

async function flushSync(node) {
    const sync = node.__stringJoinToolsRuntimeTextSync;
    if (!sync || sync.composing || sync.inFlight) return;
    clearTimeout(sync.timer);
    sync.timer = null;

    sync.inFlight = true;
    try {
        while (!sync.composing && sync.acknowledgedText !== sync.desiredText) {
            const sentText = sync.desiredText;
            if (utf8ByteCount(sentText) > MAX_TEXT_BYTES) {
                throw new Error(
                    `Text exceeds the ${MAX_TEXT_BYTES}-byte server limit`,
                );
            }

            const sequence = ++sync.nextSequence;
            setStatus(node, "SYNCING");
            const response = await api.fetchApi(LIVE_ROUTE, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    state_key: ensureUniqueStateKey(node),
                    text: sentText,
                    client_id: sync.clientId,
                    client_sequence: sequence,
                }),
            });
            if (!response.ok) throw new Error(await responseError(response));

            const payload = await response.json();
            sync.acknowledgedText = sentText;
            sync.revision = payload?.state?.revision ?? sync.revision;
            if (sync.desiredText === sentText) {
                setStatus(
                    node,
                    "LIVE",
                    sync.revision == null
                        ? "server accepted"
                        : `revision ${sync.revision}`,
                );
            }
        }
    } catch (error) {
        console.error("[StringJoinTools] Runtime text sync failed", error);
        setStatus(node, "SYNC ERROR", String(error?.message ?? error));
    } finally {
        sync.inFlight = false;
        if (
            !sync.composing &&
            sync.acknowledgedText !== sync.desiredText &&
            node.__stringJoinToolsRuntimeTextUI?.status.dataset.state !==
                "SYNC ERROR"
        ) {
            void flushSync(node);
        }
    }
}

function buildUI(node) {
    const textWidget = widgetByName(node, "text");
    const keyWidget = widgetByName(node, "state_key");
    if (!textWidget || !keyWidget) return;
    hideSavedWidget(textWidget);
    hideSavedWidget(keyWidget);
    if (node.__stringJoinToolsRuntimeTextUI) return;

    const root = document.createElement("div");
    root.style.display = "flex";
    root.style.flexDirection = "column";
    root.style.gap = "5px";
    root.style.width = "100%";
    root.style.height = "100%";
    root.style.boxSizing = "border-box";
    root.style.padding = "2px 0";

    const textarea = document.createElement("textarea");
    textarea.spellcheck = false;
    textarea.placeholder = "Text used by jobs when this node executes";
    textarea.style.width = "100%";
    textarea.style.height = "100%";
    textarea.style.minHeight = "48px";
    textarea.style.resize = "none";
    textarea.style.boxSizing = "border-box";
    textarea.style.padding = "8px";
    textarea.style.border = "1px solid rgba(255,210,70,0.35)";
    textarea.style.borderRadius = "4px";
    textarea.style.background = "rgba(60,45,0,0.18)";
    textarea.style.color = "inherit";
    textarea.style.fontFamily = "monospace";
    textarea.style.fontSize = "12px";
    textarea.style.lineHeight = "1.35";

    const footer = document.createElement("div");
    footer.style.display = "flex";
    footer.style.justifyContent = "space-between";
    footer.style.gap = "8px";
    footer.style.padding = "0 2px";
    footer.style.fontSize = "10px";

    const status = document.createElement("span");
    const count = document.createElement("span");
    count.style.marginLeft = "auto";
    footer.append(status, count);
    root.append(textarea, footer);

    const domWidget = node.addDOMWidget(
        "runtime_text_editor",
        "string-join-tools-runtime-text",
        root,
        {
            serialize: false,
            hideOnZoom: false,
            getValue: () => textarea.value,
            setValue: (value) =>
                setLocalText(node, value, { sync: true, dirty: true }),
        },
    );
    node.__stringJoinToolsRuntimeTextUI = {
        root,
        textarea,
        status,
        count,
        domWidget,
    };
    node.__stringJoinToolsRuntimeTextSync = {
        clientId: randomId("client"),
        nextSequence: 0,
        desiredText:
            typeof textWidget.value === "string" ? textWidget.value : "",
        acknowledgedText: null,
        revision: null,
        composing: false,
        inFlight: false,
        timer: null,
        editVersion: 0,
    };

    const absorbEvent = (event) => event.stopPropagation();
    for (const eventName of [
        "pointerdown",
        "mousedown",
        "mouseup",
        "click",
        "dblclick",
        "keydown",
        "keyup",
    ]) {
        textarea.addEventListener(eventName, absorbEvent);
    }
    textarea.addEventListener("compositionstart", () => {
        node.__stringJoinToolsRuntimeTextSync.composing = true;
        setStatus(node, "EDITING");
    });
    textarea.addEventListener("compositionend", () => {
        const sync = node.__stringJoinToolsRuntimeTextSync;
        sync.composing = false;
        sync.editVersion += 1;
        const value = setLocalText(node, textarea.value, { dirty: true });
        scheduleSync(node, value, true);
    });
    textarea.addEventListener("input", () => {
        const sync = node.__stringJoinToolsRuntimeTextSync;
        sync.editVersion += 1;
        const value = setLocalText(node, textarea.value, { dirty: true });
        if (sync.composing) {
            sync.desiredText = value;
            setStatus(node, "EDITING");
        } else {
            scheduleSync(node, value);
        }
    });
    textarea.addEventListener("blur", () => {
        if (!node.__stringJoinToolsRuntimeTextSync.composing) {
            scheduleSync(node, textarea.value, true);
        }
    });

    if (!textWidget.__stringJoinToolsRuntimeTextWrapped) {
        textWidget.__stringJoinToolsRuntimeTextWrapped = true;
        const originalCallback = textWidget.callback;
        textWidget.callback = function (value, ...args) {
            const result = originalCallback?.call(this, value, ...args);
            node.__stringJoinToolsRuntimeTextSync.editVersion += 1;
            setLocalText(node, value, { sync: true, dirty: true });
            return result;
        };
    }

    setLocalText(node, textWidget.value);
    setStatus(node, "SYNCING", "checking server state");
}

async function initialiseFromServer(node) {
    buildUI(node);
    if (!node.__stringJoinToolsRuntimeTextUI) return;
    if (node.__stringJoinToolsRuntimeTextInitialising) {
        return node.__stringJoinToolsRuntimeTextInitialising;
    }

    const operation = (async () => {
        const key = ensureUniqueStateKey(node);
        const sync = node.__stringJoinToolsRuntimeTextSync;
        const editVersionAtRequest = sync.editVersion;
        const response = await api.fetchApi(
            `${LIVE_ROUTE}/${encodeURIComponent(key)}`,
        );
        if (response.status === 404) {
            const fallback = setLocalText(
                node,
                widgetByName(node, "text")?.value ?? "",
            );
            sync.desiredText = fallback;
            sync.acknowledgedText = null;
            await flushSync(node);
            return;
        }
        if (!response.ok) throw new Error(await responseError(response));

        const payload = await response.json();
        const liveText = payload?.state?.text;
        if (typeof liveText !== "string") {
            throw new Error("Server returned an invalid live text state");
        }

        sync.revision = payload?.state?.revision ?? null;
        sync.acknowledgedText = liveText;
        if (sync.editVersion !== editVersionAtRequest) {
            setStatus(node, "SYNCING", "sending newer local edit");
            await flushSync(node);
            return;
        }
        sync.desiredText = liveText;
        setLocalText(node, liveText, { dirty: true });
        setStatus(
            node,
            "LIVE",
            sync.revision == null
                ? "server state restored"
                : `revision ${sync.revision}`,
        );
    })()
        .catch((error) => {
            console.error(
                "[StringJoinTools] Runtime text initialisation failed",
                error,
            );
            setStatus(node, "SYNC ERROR", String(error?.message ?? error));
        })
        .finally(() => {
            node.__stringJoinToolsRuntimeTextInitialising = null;
        });

    node.__stringJoinToolsRuntimeTextInitialising = operation;
    return operation;
}

app.registerExtension({
    name: "ruminar.StringJoinTools.RuntimeTextInput",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== TARGET_NODE) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalOnNodeCreated?.apply(this, arguments);
            setTimeout(() => void initialiseFromServer(this), 0);
            return result;
        };

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = originalOnConfigure?.apply(this, arguments);
            setTimeout(() => void initialiseFromServer(this), 0);
            return result;
        };

        const originalOnDrawBackground = nodeType.prototype.onDrawBackground;
        nodeType.prototype.onDrawBackground = function (ctx) {
            const result = originalOnDrawBackground?.apply(this, arguments);
            if (!this.flags?.collapsed) {
                ctx.save();
                ctx.fillStyle = LIVE_BACKGROUND_TINT;
                ctx.fillRect(
                    1,
                    0,
                    Math.max(0, Number(this.size?.[0] ?? 0) - 2),
                    Math.max(0, Number(this.size?.[1] ?? 0)),
                );
                ctx.restore();
            }
            return result;
        };
    },
});
