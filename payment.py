from typing import Protocol


class Payment(Protocol):
    """Payment operations used by an order."""

    def authorize(self, order_id: str) -> int: ...

    def void(self, order_id: str) -> int: ...


class StubPayment:
    """Successful payment stub; tests can mock either operation to raise."""

    def authorize(self, order_id: str) -> int:
        return 200

    def void(self, order_id: str) -> int:
        return 200
