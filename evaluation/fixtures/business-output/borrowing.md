# Community equipment library

This is synthetic acceptance-test documentation for a fictional equipment library.

Residents borrow equipment for local projects. Borrowing requires active membership and no unpaid overdue charge. Staff borrowing waives the overdue-charge requirement; active membership is still required. A waived charge requirement does not cancel the recorded charge.

Collection uses the identity check described in [Identity at collection](identity.md). A successful check is required before releasing a reserved item. A failed identity check must not be interpreted as proof of fraud.

Reservations hold an available item for 48 hours after the confirmation time. A hold expires at that deadline. An expired hold remains in reservation history; no retention duration is specified here. Cancelling before collection releases the item for another reservation.

A reservation may include several items. If one item is unavailable, the remaining items stay reserved. The resident chooses whether to remove the unavailable item or wait; the system must not substitute an item automatically.

The workshop team can request an assisted collection. The proposed evening collection service is planned but has not been approved. Do not treat the proposal as an available collection option.

Loan extensions are described in [Extensions and returns](returns.md). An extension request does not itself change the due date. The previous due date remains effective until the extension is approved.
