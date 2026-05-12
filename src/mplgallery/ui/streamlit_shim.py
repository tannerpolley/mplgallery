from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class SessionState(dict[str, Any]):
    pass


class QueryParams(dict[str, Any]):
    pass


def _identity_cache(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    _ = args, kwargs

    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        return function

    return decorator


def _no_op(*args: Any, **kwargs: Any) -> None:
    _ = args, kwargs


@dataclass
class ComponentsShim:
    def declare_component(self, name: str, path: str) -> Callable[..., None]:
        _ = name, path

        def component(**kwargs: Any) -> None:
            _ = kwargs
            return None

        return component


class StreamlitShim:
    session_state: SessionState
    query_params: QueryParams

    def __init__(self) -> None:
        self.session_state = SessionState()
        self.query_params = QueryParams()

    cache_data = staticmethod(_identity_cache)
    toast = staticmethod(_no_op)
    error = staticmethod(_no_op)
    markdown = staticmethod(_no_op)
    set_page_config = staticmethod(_no_op)

    def rerun(self) -> None:
        raise RuntimeError("rerun is not available in the Tauri compatibility shim")


st = StreamlitShim()
components = ComponentsShim()
