try:
    from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
except ImportError:  # Standalone test/import fallback.
    from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

try:
    from . import server_routes as _server_routes  # noqa: F401
except ImportError:
    try:
        import server_routes as _server_routes  # type: ignore  # noqa: F401
    except Exception as exc:
        print(f"[StringJoinTools] Runtime route registration warning: {exc}")
except Exception as exc:
    print(f"[StringJoinTools] Runtime route registration warning: {exc}")

WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
