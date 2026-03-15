import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from bmad_orch.engine.events import BaseEvent

logger = logging.getLogger("bmad_orch.engine.emitter")

class EventEmitter:
    def __init__(self) -> None:
        # event_type -> list of callbacks (ordered)
        self._subscribers: dict[type[BaseEvent], list[Callable[[Any], None]]] = defaultdict(list)
        # callback -> set of event_types it's subscribed to (for O(1) or O(log N) lookup in unsubscribe_all)
        self._callback_map: dict[Callable[[Any], None], set[type[BaseEvent]]] = defaultdict(set)

    def subscribe(self, event_type: type[BaseEvent], callback: Callable[[Any], None]) -> None:
        """
        Subscribe a callback to an event type. Idempotent (via identity check).
        """
        if not isinstance(event_type, type) or not issubclass(event_type, BaseEvent):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"event_type must be BaseEvent or a subclass of BaseEvent, got {event_type}")
        
        # AC3: Identity check 'is' for idempotency
        if not any(c is callback for c in self._subscribers[event_type]):
            self._subscribers[event_type].append(callback)
            self._callback_map[callback].add(event_type)

    def unsubscribe(self, event_type: type[BaseEvent], callback: Callable[[Any], None]) -> None:
        """
        Unsubscribe a callback from an event type. Silent no-op if not found.
        """
        subscribers = self._subscribers.get(event_type, [])
        # Find index using identity check 'is'
        idx = next((i for i, c in enumerate(subscribers) if c is callback), None)
        if idx is not None:
            subscribers.pop(idx)
            self._callback_map[callback].remove(event_type)
            if not self._callback_map[callback]:
                del self._callback_map[callback]

    def unsubscribe_all(self, callback: Callable[[Any], None]) -> None:
        """
        Remove the callback from all event types.
        """
        if callback in self._callback_map:
            # Create a list of types to iterate over, as unsubscribe modifies the map
            event_types = list(self._callback_map[callback])
            for et in event_types:
                self.unsubscribe(et, callback)

    def emit(self, event: BaseEvent) -> None:
        """
        Emit an event to all subscribers. 
        Type-specific subscribers first (registration order), then BaseEvent catch-all subscribers (registration order).
        Each unique callback is notified only once per emission.
        """
        if not isinstance(event, BaseEvent):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"event must be an instance of BaseEvent, got {type(event)}")

        event_type = type(event)
        
        # 1. Type-specific subscribers
        subscribers_to_notify = list(self._subscribers.get(event_type, []))
        
        # 2. BaseEvent catch-all subscribers (registration order)
        if event_type is not BaseEvent:
            for cb in self._subscribers.get(BaseEvent, []):
                # Deduplicate: only add if not already in the list (identity check)
                if not any(cb is already_notified for already_notified in subscribers_to_notify):
                    subscribers_to_notify.append(cb)

        for callback in subscribers_to_notify:
            try:
                callback(event)
            except Exception as e:
                # AC5: Subscriber Isolation
                callback_name = getattr(callback, "__qualname__", getattr(callback, "__name__", str(callback)))
                logger.warning(
                    "Error in subscriber %s for event type %s: %s",
                    callback_name,
                    event_type.__name__,
                    str(e),
                    exc_info=True
                )
