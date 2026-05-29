from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

try:
    import frappe
except Exception:  # pragma: no cover - local smoke tests can run without a Frappe site.
    frappe = None

MOCK_ENDPOINTS: dict[str, list[dict[str, Any]]] = {
    "material_master": [
        {
            "material_code": "MAT-000001",
            "material_name": "高速电机控制板",
            "plant": "CN01",
            "mrp_type": "PD",
            "purchasing_group": "P01",
            "product_line": "Drive",
            "source_system": "SAP_MOCK",
        },
        {
            "material_code": "MAT-000006",
            "material_name": "通用固定支架",
            "plant": "CN01",
            "mrp_type": "VB",
            "purchasing_group": "P03",
            "product_line": "Assembly",
            "source_system": "SAP_MOCK",
        },
    ],
    "purchase_requisition_items": [
        {
            "sap_object_type": "PR",
            "sap_doc_no": "1000123456",
            "sap_item_no": "00010",
            "purchase_requisition": "1000123456",
            "purchase_requisition_item": "00010",
            "material_code": "MAT-000001",
            "plant": "CN01",
            "open_qty": 12000,
            "requested_quantity": 12000,
            "requested_date": "2026-06-15",
            "delivery_date": "2026-06-15",
            "supplier": "S000982",
            "status": "Open",
        },
        {
            "sap_object_type": "PR",
            "sap_doc_no": "1000123459",
            "sap_item_no": "00030",
            "purchase_requisition": "1000123459",
            "purchase_requisition_item": "00030",
            "material_code": "MAT-000006",
            "plant": "CN01",
            "open_qty": 22000,
            "requested_quantity": 22000,
            "requested_date": "2026-06-28",
            "delivery_date": "2026-06-28",
            "supplier": "S000551",
            "status": "Open",
        },
    ],
    "purchase_order_items": [
        {
            "sap_object_type": "PO",
            "sap_doc_no": "4500098765",
            "sap_item_no": "00010",
            "purchase_order": "4500098765",
            "purchase_order_item": "00010",
            "material_code": "MAT-000003",
            "plant": "CN01",
            "confirmed": False,
            "confirmation_status": "Unconfirmed",
            "order_quantity": 8000,
            "delivery_date": "2026-06-12",
            "supplier": "S000219",
        }
    ],
    "inventory_snapshots": [
        {
            "material_code": "MAT-000001",
            "plant": "CN01",
            "storage_location": "1000",
            "available_stock": 42000,
            "quality_stock": 600,
            "blocked_stock": 0,
            "unit": "EA",
            "inventory_days": 48,
            "safety_threshold_days": 28,
            "source_snapshot": "SAP_INVENTORY_CN01_MAT-000001",
        },
        {
            "material_code": "MAT-000006",
            "plant": "CN01",
            "storage_location": "1000",
            "available_stock": 76000,
            "quality_stock": 0,
            "blocked_stock": 1200,
            "unit": "EA",
            "inventory_days": 50,
            "safety_threshold_days": 28,
            "source_snapshot": "SAP_INVENTORY_CN01_MAT-000006",
        },
    ],
}


@dataclass(frozen=True)
class SAPEndpointConfig:
    endpoint_name: str
    entity_set: str
    target_doctype: str
    key_fields: tuple[str, ...]
    business_object: str


DEFAULT_ENDPOINTS: dict[str, SAPEndpointConfig] = {
    "material_master": SAPEndpointConfig(
        endpoint_name="material_master",
        entity_set="A_ProductPlant",
        target_doctype="SAP Material Snapshot",
        key_fields=("material_code", "plant"),
        business_object="Material",
    ),
    "inventory_snapshots": SAPEndpointConfig(
        endpoint_name="inventory_snapshots",
        entity_set="A_MaterialStock",
        target_doctype="SAP Inventory Snapshot",
        key_fields=("material_code", "plant", "storage_location"),
        business_object="Inventory",
    ),
    "purchase_requisition_items": SAPEndpointConfig(
        endpoint_name="purchase_requisition_items",
        entity_set="A_PurchaseRequisitionItem",
        target_doctype="SAP PR Line",
        key_fields=("purchase_requisition", "purchase_requisition_item"),
        business_object="PR",
    ),
    "purchase_order_items": SAPEndpointConfig(
        endpoint_name="purchase_order_items",
        entity_set="A_PurchaseOrderItem",
        target_doctype="SAP PO Line",
        key_fields=("purchase_order", "purchase_order_item"),
        business_object="PO",
    ),
}

SNAPSHOT_FIELDS: dict[str, tuple[str, ...]] = {
    "SAP Material Snapshot": (
        "snapshot_id",
        "material_code",
        "material_name",
        "plant",
        "mrp_type",
        "purchasing_group",
        "product_line",
        "source_system",
        "last_synced_at",
    ),
    "SAP Inventory Snapshot": (
        "snapshot_id",
        "material_code",
        "plant",
        "storage_location",
        "available_stock",
        "quality_stock",
        "blocked_stock",
        "unit",
        "inventory_days",
        "safety_threshold_days",
        "source_snapshot",
        "last_synced_at",
    ),
    "SAP PR Line": (
        "snapshot_id",
        "purchase_requisition",
        "purchase_requisition_item",
        "material_code",
        "plant",
        "requested_quantity",
        "delivery_date",
        "supplier",
        "status",
        "last_synced_at",
    ),
    "SAP PO Line": (
        "snapshot_id",
        "purchase_order",
        "purchase_order_item",
        "material_code",
        "plant",
        "supplier",
        "order_quantity",
        "delivery_date",
        "confirmation_status",
        "last_synced_at",
    ),
}

SAP_CONNECTION_TEMPLATES: list[dict[str, Any]] = [
    {
        "connection_type": "OData",
        "title": "标准接口接入（OData）",
        "description": "通过 SAP Gateway 暴露的标准 OData API 读取物料、库存、采购申请和采购订单。",
        "required": ["SAP 网关地址", "SAP Client", "认证方式", "只读技术用户", "密码或密钥", "服务路径", "实体集", "字段映射"],
        "optional": ["OAuth 令牌地址", "OAuth Client ID", "OAuth Client Secret", "CSRF Token", "超时时间", "校验证书"],
        "security": ["账号只授予读取权限", "真实写回保持草稿模式", "接口日志不保存密码"],
    },
    {
        "connection_type": "BTP Destination",
        "title": "云目标接入（BTP Destination）",
        "description": "通过 BTP Destination 和 Cloud Connector 访问企业内网 SAP。",
        "required": ["BTP Destination 名称", "代理类型", "认证方式", "SAP Client", "Cloud Connector Location ID", "服务路径", "实体集"],
        "optional": ["Principal Propagation", "OAuth 配置", "虚拟主机", "超时时间"],
        "security": ["Destination 维护凭据", "Cloud Connector 限定虚拟主机和路径", "ChainPilot 只保存 Destination 名称"],
    },
    {
        "connection_type": "RFC",
        "title": "远程函数接入（RFC/BAPI）",
        "description": "当 OData 不可用时，通过 RFC SDK 调用只读 BAPI 或自定义函数。",
        "required": ["应用服务器地址", "系统编号", "SAP Client", "只读技术用户", "密码或密钥", "语言", "RFC 函数清单"],
        "optional": ["消息服务器", "登录组", "SAProuter 字符串", "SNC", "字段映射"],
        "security": ["需要部署 SAP NW RFC SDK", "函数白名单必须只读", "生产写回仍然禁用"],
    },
]

SAP_BUSINESS_SCOPE_PARAMETERS = [
    "公司代码",
    "工厂",
    "采购组织",
    "采购组",
    "物料类型",
    "MRP 控制员",
    "历史回溯起止日期",
    "同步时区",
]


def _whitelist(fn):
    if frappe:
        return frappe.whitelist()(fn)
    return fn


def _frappe_ready() -> bool:
    try:
        return bool(frappe and getattr(frappe.local, "site", None) and getattr(frappe, "db", None))
    except Exception:
        return False


def _now() -> str:
    if _frappe_ready():
        return str(frappe.utils.now_datetime())
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _unique_id(prefix: str, endpoint_name: str = "") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    slug = "".join(ch if ch.isalnum() else "-" for ch in endpoint_name.upper()).strip("-")[:28]
    return f"{prefix}-{slug}-{stamp}" if slug else f"{prefix}-{stamp}"


def test_connection(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return an explicit read-only SAP connection status.

    The MVP can run in mock mode before a customer SAP OData destination is configured.
    """
    config = config or {}
    mode = str(config.get("mode") or "").lower()
    if not config or mode == "disabled":
        return {"ok": False, "status": "NOT_CONFIGURED", "message": "SAP 连接尚未配置。"}
    if mode == "mock":
        return {"ok": True, "status": "MOCK_READY", "message": "正在使用模拟 SAP 只读适配器。"}
    validation = validate_connection_config(config)
    if validation["ok"]:
        return {"ok": True, "status": "CONFIG_READY", "message": "真实 SAP 参数已通过本地校验；当前仍不发起生产写回。", "validation": validation}
    return {"ok": False, "status": "DRY_RUN", "message": "真实 SAP 参数不完整，当前仅做配置校验。", "validation": validation}


def validate_connection_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    mode = str(config.get("mode") or "Mock")
    connection_type = str(config.get("connection_type") or mode or "OData")
    if mode == "Mock":
        return {"ok": True, "missing": [], "warnings": [], "connection_type": "Mock"}
    required_by_type = {
        "OData": ["base_url", "sap_client", "auth_type"],
        "BTP Destination": ["destination_name", "sap_client", "auth_type", "proxy_type"],
        "RFC": ["application_server_host", "system_number", "sap_client", "username", "password", "language"],
    }
    required = list(required_by_type.get(connection_type, required_by_type["OData"]))
    auth_type = str(config.get("auth_type") or "")
    if auth_type == "Basic":
        required += ["username", "password"]
    elif auth_type == "OAuth2":
        required += ["oauth_token_url", "oauth_client_id", "oauth_client_secret"]
    missing = [field for field in required if not config.get(field)]
    warnings = []
    if not config.get("read_only_confirmed"):
        warnings.append("需要确认技术用户只有读取权限。")
    if connection_type in {"OData", "BTP Destination"} and not config.get("csrf_enabled", True):
        warnings.append("建议启用 CSRF Token 获取，用于未来草稿写回前的安全校验。")
    if not config.get("plants"):
        warnings.append("建议先限定试点工厂，避免同步范围过大。")
    return {"ok": not missing, "missing": missing, "warnings": warnings, "connection_type": connection_type}


def get_entity_set(endpoint_name: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Read a named SAP entity set.

    Until M2 receives real SAP credentials, `params={"mode": "mock"}` returns deterministic mock rows
    that match the imported demo recommendations. Production SAP writes are intentionally unsupported.
    """
    params = params or {}
    if params.get("mode") != "mock":
        return []
    rows = MOCK_ENDPOINTS.get(endpoint_name, [])
    filters = {key: value for key, value in params.items() if key != "mode"}
    if not filters:
        return [row.copy() for row in rows]
    return [row.copy() for row in rows if all(row.get(key) == value for key, value in filters.items())]


def sync_endpoint(endpoint_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Synchronize one read-only SAP endpoint into a local Snapshot DocType.

    With `params={"mode": "mock"}` this writes deterministic mock rows when a Frappe site
    is available. With no site or `dry_run=True`, it returns the mapped payloads without
    touching the database. Non-mock modes deliberately remain dry-run until customer SAP
    read-only credentials are supplied.
    """
    params = params or {}
    if endpoint_name not in DEFAULT_ENDPOINTS:
        raise ValueError(f"Unknown SAP endpoint: {endpoint_name}")

    config = DEFAULT_ENDPOINTS[endpoint_name]
    mode = str(params.get("mode") or "mock").lower()
    dry_run = bool(params.get("dry_run")) or not _frappe_ready()
    job_id = None
    api_log_id = None
    started_at = _now()
    started_perf = perf_counter()

    if mode != "mock":
        result = {
            "endpoint_name": endpoint_name,
            "status": "DRY_RUN",
            "mode": "Dry Run",
            "target_doctype": config.target_doctype,
            "rows_read": 0,
            "rows_upserted": 0,
            "job_id": None,
            "api_log_id": None,
            "message": "真实 SAP 账号和服务未配置前，不会调用正式接口。",
        }
        if _frappe_ready():
            _write_api_log(config, None, result, started_at, error_message=result["message"])
        return result

    filters = {key: value for key, value in params.items() if key not in {"mode", "dry_run"}}
    rows = get_entity_set(endpoint_name, {"mode": "mock", **filters})
    mapped_rows = [_map_to_snapshot(endpoint_name, row) for row in rows]

    if _frappe_ready() and not dry_run:
        ensure_mock_configuration()
        job_id = _create_sync_job(config, started_at, filters)

    upserted = 0
    for payload in mapped_rows:
        if _frappe_ready() and not dry_run:
            _upsert_frappe_doc(config.target_doctype, payload)
        upserted += 1

    finished_at = _now()
    result = {
        "endpoint_name": endpoint_name,
        "status": "Success",
        "mode": "Mock" if not dry_run else "Dry Run",
        "target_doctype": config.target_doctype,
        "rows_read": len(rows),
        "rows_upserted": upserted,
        "job_id": job_id,
        "api_log_id": api_log_id,
        "sample": mapped_rows[:2],
    }

    if _frappe_ready() and not dry_run:
        _finish_sync_job(job_id, finished_at, result)
        api_log_id = _write_api_log(config, job_id, result, started_at, duration_ms=int((perf_counter() - started_perf) * 1000))
        result["api_log_id"] = api_log_id
        frappe.db.commit()
    return result


def upsert_snapshot(target_doctype: str, row: dict[str, Any], key_fields: list[str]) -> str:
    """Build the deterministic key that a Frappe upsert will use in M2."""
    missing = [field for field in key_fields if field not in row]
    if missing:
        raise ValueError(f"Missing key fields for snapshot upsert: {', '.join(missing)}")
    return "::".join(str(row[field]) for field in key_fields)


def _map_to_snapshot(endpoint_name: str, row: dict[str, Any]) -> dict[str, Any]:
    config = DEFAULT_ENDPOINTS[endpoint_name]
    snapshot_id = upsert_snapshot(config.target_doctype, row, list(config.key_fields))
    allowed_fields = SNAPSHOT_FIELDS[config.target_doctype]
    payload = {field: row.get(field) for field in allowed_fields if field in row}
    payload["snapshot_id"] = snapshot_id
    payload["last_synced_at"] = _now()
    return payload


def _upsert_frappe_doc(target_doctype: str, payload: dict[str, Any]) -> str:
    existing_name = frappe.db.exists(target_doctype, payload["snapshot_id"])
    if existing_name:
        doc = frappe.get_doc(target_doctype, existing_name)
        doc.update(payload)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc({"doctype": target_doctype, **payload})
    doc.insert(ignore_permissions=True)
    return doc.name


def _create_sync_job(config: SAPEndpointConfig, started_at: str, filters: dict[str, Any]) -> str:
    job_id = _unique_id("SYNC", config.endpoint_name)
    doc = frappe.get_doc(
        {
            "doctype": "SAP Sync Job",
            "job_id": job_id,
            "endpoint": config.endpoint_name,
            "status": "Running",
            "mode": "Mock",
            "started_at": started_at,
            "request_filter_json": frappe.as_json(filters) if filters else "{}",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _finish_sync_job(job_id: str | None, finished_at: str, result: dict[str, Any]) -> None:
    if not job_id:
        return
    doc = frappe.get_doc("SAP Sync Job", job_id)
    doc.status = result["status"]
    doc.finished_at = finished_at
    doc.rows_read = result["rows_read"]
    doc.rows_upserted = result["rows_upserted"]
    doc.save(ignore_permissions=True)


def _write_api_log(
    config: SAPEndpointConfig,
    job_id: str | None,
    result: dict[str, Any],
    started_at: str,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> str | None:
    if not _frappe_ready():
        return None
    api_log_id = _unique_id("SAPLOG", config.endpoint_name)
    duration_ms = 0 if duration_ms is None else duration_ms
    doc = frappe.get_doc(
        {
            "doctype": "SAP API Log",
            "api_log_id": api_log_id,
            "endpoint": config.endpoint_name,
            "job_id": job_id,
            "mode": result.get("mode", "Mock"),
            "method": "GET",
            "url": f"mock://{config.entity_set}",
            "status_code": 200 if result.get("status") == "Success" else 0,
            "duration_ms": duration_ms,
            "request_summary": f"SAP 实体集 {config.entity_set}；目标快照表 {config.target_doctype}",
            "response_summary": f"读取 {result.get('rows_read', 0)} 行；写入或更新 {result.get('rows_upserted', 0)} 行",
            "error_message": error_message,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _endpoint_doc(config: SAPEndpointConfig) -> dict[str, Any]:
    service_path = {
        "material_master": "/sap/opu/odata/sap/API_PRODUCT_SRV",
        "inventory_snapshots": "/sap/opu/odata/sap/API_MATERIAL_STOCK_SRV",
        "purchase_requisition_items": "/sap/opu/odata/sap/API_PURCHASEREQ_PROCESS_SRV",
        "purchase_order_items": "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV",
    }[config.endpoint_name]
    return {
        "doctype": "SAP Endpoint",
        "endpoint_name": config.endpoint_name,
        "business_object": config.business_object,
        "enabled": 1,
        "service_path": service_path,
        "entity_set": config.entity_set,
        "target_doctype": config.target_doctype,
        "key_fields": ",".join(config.key_fields),
        "filter_json": '{"Plant":"CN01"}',
        "page_size": 200,
        "sync_frequency": "Manual",
        "field_mappings": [
            {"source_field": field, "target_field": field, "required": 1 if field in config.key_fields else 0}
            for field in SNAPSHOT_FIELDS[config.target_doctype]
            if field not in {"snapshot_id", "last_synced_at"}
        ],
    }


@_whitelist
def ensure_mock_configuration() -> dict[str, Any]:
    """Create the M2 mock connection and default endpoint records for a Frappe site."""
    if not _frappe_ready():
        return {"ok": False, "status": "NO_SITE", "created": 0, "updated": 0}

    created = 0
    updated = 0
    connection = frappe.get_single("SAP Connection")
    connection.mode = "Mock"
    if hasattr(connection, "connection_type"):
        connection.connection_type = "OData"
    connection.auth_type = "None"
    connection.timeout_seconds = 30
    connection.verify_ssl = 1
    if hasattr(connection, "csrf_enabled"):
        connection.csrf_enabled = 1
    if hasattr(connection, "timezone"):
        connection.timezone = "Asia/Shanghai"
    if hasattr(connection, "plants"):
        connection.plants = "CN01"
    connection.last_test_status = "Mock Ready"
    connection.last_test_message = "正在使用确定性模拟 SAP 只读适配器。"
    connection.last_test_at = _now()
    connection.save(ignore_permissions=True)

    for config in DEFAULT_ENDPOINTS.values():
        payload = _endpoint_doc(config)
        if frappe.db.exists("SAP Endpoint", config.endpoint_name):
            doc = frappe.get_doc("SAP Endpoint", config.endpoint_name)
            doc.update({key: value for key, value in payload.items() if key not in {"doctype", "field_mappings"}})
            doc.set("field_mappings", [])
            for mapping in payload["field_mappings"]:
                doc.append("field_mappings", mapping)
            doc.save(ignore_permissions=True)
            updated += 1
        else:
            doc = frappe.get_doc(payload)
            doc.insert(ignore_permissions=True)
            created += 1

    frappe.db.commit()
    return {"ok": True, "status": "MOCK_CONFIG_READY", "created": created, "updated": updated}


@_whitelist
def test_connection_rpc(mode: str = "mock") -> dict[str, Any]:
    config = {"mode": mode}
    if _frappe_ready() and mode.lower() != "mock":
        connection = frappe.get_single("SAP Connection")
        config = {
            "mode": connection.mode if connection.mode != "Mock" else mode,
            "connection_type": getattr(connection, "connection_type", "OData"),
            "base_url": getattr(connection, "base_url", None),
            "destination_name": getattr(connection, "destination_name", None),
            "sap_client": getattr(connection, "sap_client", None),
            "auth_type": getattr(connection, "auth_type", None),
            "username": getattr(connection, "username", None),
            "password": getattr(connection, "password", None),
            "oauth_token_url": getattr(connection, "oauth_token_url", None),
            "oauth_client_id": getattr(connection, "oauth_client_id", None),
            "oauth_client_secret": getattr(connection, "oauth_client_secret", None),
            "proxy_type": getattr(connection, "proxy_type", None),
            "application_server_host": getattr(connection, "application_server_host", None),
            "system_number": getattr(connection, "system_number", None),
            "language": getattr(connection, "language", None),
            "read_only_confirmed": getattr(connection, "read_only_confirmed", None),
            "csrf_enabled": getattr(connection, "csrf_enabled", None),
            "plants": getattr(connection, "plants", None),
        }
    result = test_connection(config)
    if _frappe_ready():
        connection = frappe.get_single("SAP Connection")
        connection.mode = "Mock" if mode.lower() == "mock" else "OData"
        if hasattr(connection, "connection_type") and not connection.connection_type:
            connection.connection_type = "OData"
        connection.last_test_status = "Mock Ready" if result.get("status") == "MOCK_READY" else "Config Ready" if result.get("status") == "CONFIG_READY" else "Dry Run"
        connection.last_test_message = result["message"]
        connection.last_test_at = _now()
        connection.save(ignore_permissions=True)
        frappe.db.commit()
    return result


@_whitelist
def run_mock_sync(endpoint_name: str = "all") -> dict[str, Any]:
    if _frappe_ready():
        ensure_mock_configuration()
    endpoint_names = list(DEFAULT_ENDPOINTS) if endpoint_name == "all" else [endpoint_name]
    results = [sync_endpoint(name, {"mode": "mock"}) for name in endpoint_names]
    return {
        "ok": all(item["status"] == "Success" for item in results),
        "results": results,
        "rows_read": sum(item["rows_read"] for item in results),
        "rows_upserted": sum(item["rows_upserted"] for item in results),
    }


@_whitelist
def get_sync_dashboard() -> dict[str, Any]:
    if not _frappe_ready():
        return {
            "ok": True,
            "connection": test_connection({"mode": "mock"}),
            "endpoints": [config.__dict__ for config in DEFAULT_ENDPOINTS.values()],
            "counts": {config.target_doctype: len(MOCK_ENDPOINTS[config.endpoint_name]) for config in DEFAULT_ENDPOINTS.values()},
            "connection_templates": SAP_CONNECTION_TEMPLATES,
            "business_scope_parameters": SAP_BUSINESS_SCOPE_PARAMETERS,
            "readiness": validate_connection_config({"mode": "Mock"}),
            "jobs": [],
            "logs": [],
        }

    ensure_mock_configuration()
    connection = frappe.get_single("SAP Connection")
    counts = {
        config.target_doctype: frappe.db.count(config.target_doctype)
        for config in DEFAULT_ENDPOINTS.values()
    }
    endpoints = frappe.get_all(
        "SAP Endpoint",
        fields=["endpoint_name", "business_object", "entity_set", "target_doctype", "enabled", "sync_frequency"],
        order_by="modified desc",
    )
    jobs = frappe.get_all(
        "SAP Sync Job",
        fields=["job_id", "endpoint", "status", "mode", "started_at", "finished_at", "rows_read", "rows_upserted"],
        order_by="started_at desc",
        limit=8,
    )
    logs = frappe.get_all(
        "SAP API Log",
        fields=["api_log_id", "endpoint", "job_id", "status_code", "duration_ms", "response_summary", "error_message"],
        order_by="modified desc",
        limit=4,
    )
    return {
        "ok": True,
        "connection": {
            "mode": connection.mode,
            "connection_type": getattr(connection, "connection_type", "OData"),
            "base_url": getattr(connection, "base_url", None),
            "destination_name": getattr(connection, "destination_name", None),
            "sap_client": getattr(connection, "sap_client", None),
            "auth_type": getattr(connection, "auth_type", None),
            "proxy_type": getattr(connection, "proxy_type", None),
            "plants": getattr(connection, "plants", None),
            "company_codes": getattr(connection, "company_codes", None),
            "purchasing_organizations": getattr(connection, "purchasing_organizations", None),
            "read_only_confirmed": getattr(connection, "read_only_confirmed", None),
            "csrf_enabled": getattr(connection, "csrf_enabled", None),
            "last_test_status": connection.last_test_status,
            "last_test_message": connection.last_test_message,
            "last_test_at": connection.last_test_at,
        },
        "counts": counts,
        "endpoints": endpoints,
        "connection_templates": SAP_CONNECTION_TEMPLATES,
        "business_scope_parameters": SAP_BUSINESS_SCOPE_PARAMETERS,
        "readiness": validate_connection_config(
            {
                "mode": connection.mode,
                "connection_type": getattr(connection, "connection_type", "OData"),
                "base_url": getattr(connection, "base_url", None),
                "destination_name": getattr(connection, "destination_name", None),
                "sap_client": getattr(connection, "sap_client", None),
                "auth_type": getattr(connection, "auth_type", None),
                "username": getattr(connection, "username", None),
                "password": getattr(connection, "password", None),
                "oauth_token_url": getattr(connection, "oauth_token_url", None),
                "oauth_client_id": getattr(connection, "oauth_client_id", None),
                "oauth_client_secret": getattr(connection, "oauth_client_secret", None),
                "proxy_type": getattr(connection, "proxy_type", None),
                "application_server_host": getattr(connection, "application_server_host", None),
                "system_number": getattr(connection, "system_number", None),
                "language": getattr(connection, "language", None),
                "read_only_confirmed": getattr(connection, "read_only_confirmed", None),
                "csrf_enabled": getattr(connection, "csrf_enabled", None),
                "plants": getattr(connection, "plants", None),
            }
        ),
        "jobs": jobs,
        "logs": logs,
    }
