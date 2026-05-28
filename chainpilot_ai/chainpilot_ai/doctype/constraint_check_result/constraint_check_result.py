try:
    from frappe.model.document import Document
except ModuleNotFoundError:
    class Document:  # type: ignore[no-redef]
        pass


class ConstraintCheckResult(Document):
    pass
