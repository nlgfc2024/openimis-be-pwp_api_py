def bind_service_signals():
    """openIMIS discovery hook. No domain signals are bound in the skeleton.

    Future adapters should bind their own domain services and call
    notifications.publish_resource() with a resource name and stable primary key.
    """
