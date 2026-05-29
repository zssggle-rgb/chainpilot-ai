# Mock 验收集与 SAP 接入升级说明

## 1. Mock 数据改造

当前默认 Mock 快照由 `chainpilot_ai.snapshots.realistic_mock.build_realistic_mock_sap_snapshot` 生成，不再使用几条演示行作为默认算法输入。

覆盖范围：

| 数据域 | 行数 |
| --- | ---: |
| 物料 | 18 |
| 库存 | 18 |
| 采购申请 | 32 |
| 采购订单 | 28 |
| BOM | 18 |
| 计划需求 | 51 |
| 消耗历史 | 144 |
| 供应商履约 | 108 |
| MRP 参数 | 18 |

内置约束案例：

- 冻结期内 PR/PO 阻断。
- MOQ/MPQ 阻断。
- 保护物料阻断。
- 供应商已确认订单进入确认分层。
- 同一物料多 PR/PO 共享服务水平余量。
- 动作数量、复核数量、供应商确认数量和审批金额容量限制。

页面入口：

```text
/app/mock-data-center
```

## 2. 现金优化算法升级

`chainpilot_ai.algorithms.cash_release_pr_po` 已从简单排序升级为整数规划求解：

- 候选动作：取消/下调 PR，延期 PO。
- 硬约束：保护物料、冻结期、MOQ/MPQ、服务水平余量。
- 全局约束：最多动作数、最多复核数、最多供应商确认数、审批金额容量、同物料余量。
- 目标函数：最大化资金改善，扣减风险惩罚和供应商确认惩罚。
- 求解器：优先使用 SciPy HiGHS MILP；运行环境没有 SciPy 时使用同一约束模型的精确整数枚举。

当前本地 Mock 结果：

- 缺料召回率：100%
- 高风险准确率：96%
- 误干预率：4%
- 推荐策略硬约束违规：0
- 现金优化求解状态：HiGHS MILP / OPTIMAL

这说明 mock 阶段已经能展示“真实算法在约束验收集上跑出好结果”。生产上线仍需用两年真实 SAP 历史回测确认阈值。

## 3. SAP 接入配置升级

`SAP Connection` 已补充真实接入字段，页面 `/app/sap-integration-console` 会展示三类接入模板：

| 接入方式 | 必填参数 |
| --- | --- |
| OData | SAP 网关地址、SAP Client、认证方式、只读技术用户、密码或密钥、服务路径、实体集、字段映射 |
| BTP Destination | Destination 名称、代理类型、认证方式、SAP Client、Cloud Connector Location ID、服务路径、实体集 |
| RFC/BAPI | 应用服务器地址、系统编号、SAP Client、只读技术用户、密码或密钥、语言、RFC 函数清单 |

业务范围参数：

- 公司代码
- 工厂
- 采购组织
- 采购组
- 物料类型
- MRP 控制员
- 历史回溯起止日期
- 同步时区

安全边界：

- 生产账号必须只读。
- 系统只做数据同步和回写草稿，不自动写 SAP。
- 接口日志不保存密码或密钥。
