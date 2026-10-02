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

    def advance(self) -> None:
        if self.state == "initialized":
            try:
                self.payment.authorize(self.order_id)
            except PaymentDeclined:
                self._set_state("rejected")
            else:
                self._set_state("payment_authorized")
        elif self.state == "payment_authorized":
            try:
                self.complete_order(self.order_id)
            except CompletionFailed:
                self.payment.void(self.order_id)
                self._set_state("cancelled")
            else:
                self._set_state("complete")
        else:
            raise ValueError(f"Cannot advance order in state {self.state!r}")
