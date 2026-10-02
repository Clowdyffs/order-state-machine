from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from payment import Payment


class PaymentDeclined(Exception):
    """Payment authorization was declined."""


class CompletionFailed(Exception):
    """The order could not be completed."""


class VoidFailed(Exception):
    """The authorized payment could not be voided."""


@dataclass
class Order:
    order_id: str
    payment: Payment
    complete_order: Callable[[str], int]
    state: str = field(init=False, default="initialized")
    history: list[tuple[str, datetime]] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self._set_state(self.state)

    def _set_state(self, state: str) -> None:
        self.state = state
        self.history.append((state, datetime.now(timezone.utc)))
