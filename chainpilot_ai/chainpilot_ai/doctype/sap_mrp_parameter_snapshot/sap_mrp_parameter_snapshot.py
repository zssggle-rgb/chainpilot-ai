from __future__ import annotations

try:
    from frappe.model.document import Document
except ModuleNotFoundError:
    class Document:  # type: ignore[no-redef]
        pass


class SAPMRPParameterSnapshot(Document):
    pass
