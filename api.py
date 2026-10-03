"""In-memory API: run one worker; orders are lost when the process exits."""

from datetime import datetime
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from order import InvalidTransition, Order, VoidFailed
from payment import StubPayment

app = FastAPI(title="Order State Machine")
orders: dict[str, Order] = {}
orders_lock = Lock()
payment = StubPayment()


class OrderResponse(BaseModel):
    order_id: str
    state: str
    history: list[tuple[str, datetime]]


def complete_order(order_id: str) -> int:
    """Successful completion stub."""
    return 200


def _get_order(order_id: str) -> Order:
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _snapshot(order: Order) -> OrderResponse:
    return OrderResponse(
        order_id=order.order_id, state=order.state, history=order.history
    )


@app.post("/orders", status_code=201)
def create_order() -> OrderResponse:
    with orders_lock:
        order = Order(str(uuid4()), payment=payment, complete_order=complete_order)
        orders[order.order_id] = order
        return _snapshot(order)


@app.post("/orders/{order_id}/advance")
def advance_order(order_id: str) -> OrderResponse:
    with orders_lock:
        order = _get_order(order_id)
        try:
            order.advance()
        except VoidFailed as error:
            raise HTTPException(
                status_code=502,
                detail={"error": str(error), "state": order.state},
            ) from error
        except InvalidTransition as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return _snapshot(order)


@app.get("/orders/{order_id}")
def read_order(order_id: str) -> OrderResponse:
    with orders_lock:
        return _snapshot(_get_order(order_id))
