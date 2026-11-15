"""Typed refusal for delivery."""


class DeliveryRefused(Exception):
    """A delivery step refused its input; the message names the subject, never an absolute path."""
