from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import api
from order import CompletionFailed, VoidFailed


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "orders", {})
    with TestClient(api.app) as client:
        yield client


def test_order_lifecycle(client):
    response = client.post("/orders")
    assert response.status_code == 201
    created = response.json()
    path = f"/orders/{created['order_id']}"
    assert created["state"] == "initialized"
    assert client.get(path).json() == created

    response = client.post(f"{path}/advance")
    assert response.status_code == 200
    assert response.json()["state"] == "payment_authorized"

    response = client.post(f"{path}/advance")
    assert response.status_code == 200
    completed = response.json()
    assert completed["state"] == "complete"
    assert [state for state, _ in completed["history"]] == [
        "initialized", "payment_authorized", "complete"
    ]
    assert all(
        datetime.fromisoformat(timestamp).utcoffset() is not None
        for _, timestamp in completed["history"]
    )
    assert client.post(f"{path}/advance").status_code == 409
    assert client.get(path).json() == completed


def test_unexpected_completion_error_returns_server_error(client, monkeypatch):
    monkeypatch.setattr(
        api, "complete_order", Mock(side_effect=ValueError("unexpected error"))
    )
    order_id = client.post("/orders").json()["order_id"]
    path = f"/orders/{order_id}"
    assert client.post(f"{path}/advance").status_code == 200

    with TestClient(api.app, raise_server_exceptions=False) as error_client:
        response = error_client.post(f"{path}/advance")

    assert response.status_code == 500
    assert client.get(path).json()["state"] == "payment_authorized"


@pytest.mark.parametrize("method, suffix", [("GET", ""), ("POST", "/advance")])
def test_missing_order(client, method, suffix):
    response = client.request(method, f"/orders/missing{suffix}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_failed_void_is_visible_and_order_remains_queryable(client, monkeypatch):
    payment = Mock(spec=["authorize", "void"])
    payment.authorize.return_value = 200
    payment.void.side_effect = VoidFailed("void failed")
    monkeypatch.setattr(api, "payment", payment)
    monkeypatch.setattr(
        api, "complete_order", Mock(side_effect=CompletionFailed("completion failed"))
    )
    order_id = client.post("/orders").json()["order_id"]
    path = f"/orders/{order_id}"
    assert client.post(f"{path}/advance").status_code == 200

    response = client.post(f"{path}/advance")
    assert response.status_code == 502
    assert response.json()["detail"] == {
        "error": "void failed", "state": "needs_attention"
    }
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["state"] == "needs_attention"
    assert [state for state, _ in response.json()["history"]] == [
        "initialized", "payment_authorized", "needs_attention"
    ]


def test_concurrent_advances_do_not_repeat_payment(client, monkeypatch):
    payment = Mock(spec=["authorize", "void"])
    payment.authorize.return_value = 200
    complete_order = Mock(return_value=200)
    monkeypatch.setattr(api, "payment", payment)
    monkeypatch.setattr(api, "complete_order", complete_order)
    order_id = client.post("/orders").json()["order_id"]
    barrier = Barrier(2)

    def advance():
        with TestClient(api.app) as concurrent_client:
            barrier.wait(timeout=5)
            return concurrent_client.post(f"/orders/{order_id}/advance")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(advance) for _ in range(2)]
        responses = [future.result(timeout=10) for future in futures]

    assert all(response.status_code == 200 for response in responses)
    assert sorted(response.json()["state"] for response in responses) == [
        "complete", "payment_authorized"
    ]
    payment.authorize.assert_called_once_with(order_id)
    payment.void.assert_not_called()
    complete_order.assert_called_once_with(order_id)
