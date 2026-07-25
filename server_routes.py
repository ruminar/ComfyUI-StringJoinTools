from __future__ import annotations

try:
    from aiohttp import web
    from server import PromptServer
except ImportError:
    web = None
    PromptServer = None

try:
    from .runtime_state import RUNTIME_STATE_STORE
except ImportError:
    from runtime_state import RUNTIME_STATE_STORE


if PromptServer is not None and web is not None:

    @PromptServer.instance.routes.post("/string_join_tools/runtime_state")
    async def update_runtime_state(request):
        try:
            data = await request.json()
            state = RUNTIME_STATE_STORE.update(
                state_key=data.get("state_key", ""),
                mode=data.get("mode", "multiple"),
                enabled_mask=int(data.get("enabled_mask", 0)),
                selected_index=int(data.get("selected_index", -1)),
                input_count=int(data.get("input_count", 10)),
            )
            return web.json_response({"ok": True, "state": state.to_dict()})
        except (TypeError, ValueError) as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:
            return web.json_response(
                {"ok": False, "error": f"Unexpected runtime state error: {exc}"},
                status=500,
            )

    @PromptServer.instance.routes.get("/string_join_tools/runtime_state/{state_key}")
    async def read_runtime_state(request):
        state_key = request.match_info.get("state_key", "")
        state = RUNTIME_STATE_STORE.get(state_key)
        if state is None:
            return web.json_response(
                {"ok": False, "error": "Runtime state not found"},
                status=404,
            )
        return web.json_response({"ok": True, "state": state.to_dict()})
