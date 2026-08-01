import { app } from "../../scripts/app.js";

const TARGET_NODE = "StringJoinTools_StringOutput";

function firstValue(value, fallback = "") {
    if (Array.isArray(value)) {
        if (value.length === 0) return fallback;
        return firstValue(value[0], fallback);
    }
    return value ?? fallback;
}

app.registerExtension({
    name: "ruminar.StringJoinTools.StringOutput",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== TARGET_NODE) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalOnNodeCreated?.apply(this, arguments);

            if (this.__stringJoinToolsOutput) return result;

            const container = document.createElement("div");
            container.style.display = "flex";
            container.style.flexDirection = "column";
            container.style.gap = "4px";
            container.style.width = "100%";
            container.style.height = "100%";
            container.style.boxSizing = "border-box";

            const textarea = document.createElement("textarea");
            textarea.readOnly = true;
            textarea.spellcheck = false;
            textarea.placeholder = "Run the workflow to display text.";
            textarea.style.width = "100%";
            textarea.style.minHeight = "110px";
            textarea.style.height = "100%";
            textarea.style.resize = "vertical";
            textarea.style.boxSizing = "border-box";
            textarea.style.padding = "8px";
            textarea.style.border = "1px solid rgba(255,255,255,0.15)";
            textarea.style.borderRadius = "4px";
            textarea.style.background = "rgba(0,0,0,0.18)";
            textarea.style.color = "inherit";
            textarea.style.fontFamily = "monospace";
            textarea.style.fontSize = "12px";
            textarea.style.lineHeight = "1.35";

            const status = document.createElement("div");
            status.textContent = "Not executed";
            status.style.fontSize = "11px";
            status.style.opacity = "0.65";
            status.style.padding = "0 2px";

            container.append(textarea, status);

            const widget = this.addDOMWidget(
                "string_output_preview",
                "string-join-tools-output",
                container,
                {
                    serialize: false,
                    hideOnZoom: false,
                    getValue: () => textarea.value,
                    setValue: (value) => {
                        textarea.value = String(value ?? "");
                    },
                },
            );

            this.__stringJoinToolsOutput = {
                container,
                textarea,
                status,
                widget,
            };

            return result;
        };

        const originalOnExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            originalOnExecuted?.apply(this, arguments);

            const output = this.__stringJoinToolsOutput;
            if (!output) return;

            const text = String(firstValue(message?.text, ""));
            const reportedLength = Number(firstValue(message?.length, text.length));
            const length = Number.isFinite(reportedLength)
                ? reportedLength
                : text.length;

            output.textarea.value = text;
            output.status.textContent =
                length === 0
                    ? "Empty string · 0 characters"
                    : `${length} characters`;

            this.setDirtyCanvas?.(true, true);
            app.graph?.setDirtyCanvas?.(true, false);
        };
    },
});
