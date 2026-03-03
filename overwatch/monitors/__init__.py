"""Monitor framework: BaseMonitor, registry, factory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type

from rich.text import Text

# Registry: type string → monitor class
_REGISTRY: dict[str, Type[BaseMonitor]] = {}


def register_monitor(type_name: str):
    """Decorator to register a monitor class."""
    def decorator(cls: Type[BaseMonitor]) -> Type[BaseMonitor]:
        _REGISTRY[type_name] = cls
        return cls
    return decorator


class BaseMonitor(ABC):
    """Base class for all monitors."""

    title: str = "Monitor"
    refresh_interval: float = 2.0

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        if "refresh" in self.config:
            self.refresh_interval = float(self.config["refresh"])

    @abstractmethod
    async def poll(self) -> Text | str:
        """Poll and return renderable content."""
        ...

    async def start(self) -> None:
        """Called when monitor starts."""
        pass

    async def stop(self) -> None:
        """Called when monitor stops."""
        pass


def create_monitor(type_name: str, config: dict[str, Any]) -> BaseMonitor:
    """Create a monitor instance by type name."""
    # Ensure all monitor modules are imported
    import overwatch.monitors.process_stats
    import overwatch.monitors.custom_metrics
    import overwatch.monitors.file_watcher
    import overwatch.monitors.http_health

    cls = _REGISTRY.get(type_name)
    if cls is None:
        raise ValueError(f"Unknown monitor type: {type_name!r}. Available: {list(_REGISTRY.keys())}")
    return cls(config)
