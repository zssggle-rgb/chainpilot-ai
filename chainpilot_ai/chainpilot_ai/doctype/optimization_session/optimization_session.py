try:
    from frappe.model.document import Document
except ModuleNotFoundError:  # Allows local static tests without a bench environment.
    class Document:  # type: ignore[no-redef]
        pass


class OptimizationSession(Document):
    pass
