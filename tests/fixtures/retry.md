# Notification delivery

The notification service delivers customer messages.

## Retry rules

| Failure | Attempts | Condition |
| --- | --- | --- |
| Transient | 3 | Only while delivery remains enabled |
| Permanent | 0 | Never retry |

The customer must provide a sender address before activation.

See [Retry rules](#retry-rules).
