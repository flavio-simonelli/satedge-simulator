"""Tests of the bus of the notifications."""

from satedge_simulator.observe.bus import EventBus
from satedge_simulator.observe.notifications import (
    Notification,
    RequestArrived,
    RequestFailed,
)


def test_a_subscriber_hears_only_its_type() -> None:
    bus = EventBus()
    heard: list[RequestArrived] = []
    bus.subscribe(RequestArrived, heard.append)
    bus.publish(RequestArrived(1.0, "R1"))
    bus.publish(RequestFailed(2.0, "R1"))
    assert heard == [RequestArrived(1.0, "R1")]


def test_a_subscriber_of_every_notification_hears_them_all_in_order() -> None:
    bus = EventBus()
    heard: list[Notification] = []
    bus.subscribe(Notification, heard.append)
    bus.publish(RequestArrived(1.0, "R1"))
    bus.publish(RequestFailed(2.0, "R1"))
    assert heard == [RequestArrived(1.0, "R1"), RequestFailed(2.0, "R1")]


def test_subscribers_hear_in_subscription_order() -> None:
    bus = EventBus()
    order: list[str] = []
    bus.subscribe(RequestArrived, lambda _: order.append("first"))
    bus.subscribe(Notification, lambda _: order.append("all"))
    bus.subscribe(RequestArrived, lambda _: order.append("second"))
    bus.publish(RequestArrived(1.0, "R1"))
    assert order == ["first", "second", "all"]


def test_publishing_without_subscribers_does_nothing() -> None:
    EventBus().publish(RequestArrived(1.0, "R1"))
