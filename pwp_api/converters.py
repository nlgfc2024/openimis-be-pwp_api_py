from abc import ABC, abstractmethod


class ResourceConverter(ABC):
    """Stable external contracts belong here, not in domain models."""

    def __init__(self, user):
        self.user = user

    @abstractmethod
    def to_representation(self, instance):
        """Return only explicitly allowed JSON fields for this actor."""

    def to_internal_value(self, data):
        raise NotImplementedError("Write conversion must be implemented explicitly")
