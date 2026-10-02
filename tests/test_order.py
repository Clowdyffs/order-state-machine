from datetime import datetime
from unittest.mock import Mock, call

import pytest

from order import CompletionFailed, Order, PaymentDeclined, VoidFailed


@pytest.fixture
def checkout():
    payment = Mock(spec=["authorize", "void"])
    payment.authorize.return_value = 200
    payment.void.return_value = 200
    complete_order = Mock(return_value=200)
    order = Order("order-1", payment=payment, complete_order=complete_order)
    return order, payment, complete_order


def assert_history(order, states):
    assert [state for state, _ in order.history] == states
    timestamps = [timestamp for _, timestamp in order.history]
    assert all(isinstance(timestamp, datetime) for timestamp in timestamps)
    assert timestamps == sorted(timestamps)


def test_happy_path(checkout):
    order, payment, complete_order = checkout
    assert order.state == "initialized"

    order.advance()
    assert order.state == "payment_authorized"
    payment.authorize.assert_called_once_with("order-1")
    complete_order.assert_not_called()

    order.advance()
    assert order.state == "complete"
    complete_order.assert_called_once_with("order-1")
    payment.void.assert_not_called()
    assert_history(order, ["initialized", "payment_authorized", "complete"])


def test_payment_decline(checkout):
    order, payment, complete_order = checkout
    payment.authorize.side_effect = PaymentDeclined("payment declined")

    order.advance()

    assert order.state == "rejected"
    payment.authorize.assert_called_once_with("order-1")
    payment.void.assert_not_called()
    complete_order.assert_not_called()
    assert_history(order, ["initialized", "rejected"])


def test_completion_failure_with_successful_void(checkout):
    order, payment, complete_order = checkout
    complete_order.side_effect = CompletionFailed("completion failed")

    order.advance()
    order.advance()

    assert order.state == "cancelled"
    assert payment.mock_calls == [call.authorize("order-1"), call.void("order-1")]
    complete_order.assert_called_once_with("order-1")
    assert_history(order, ["initialized", "payment_authorized", "cancelled"])


def test_completion_failure_with_failed_void(checkout):
    order, payment, complete_order = checkout
    complete_order.side_effect = CompletionFailed("completion failed")
    payment.void.side_effect = VoidFailed("void failed")

    order.advance()
    with pytest.raises(VoidFailed, match="void failed"):
        order.advance()

    assert order.state == "needs_attention"
    assert payment.mock_calls == [call.authorize("order-1"), call.void("order-1")]
    complete_order.assert_called_once_with("order-1")
    assert_history(order, ["initialized", "payment_authorized", "needs_attention"])
