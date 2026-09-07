# Run manifest

默认位置为 `<run-dir>/report/run_manifest.json`。路径均相对于 run directory；不允许 `..` 越界或绝对路径。

## 最小示例

```json
{
  "schema_version": "1.0",
  "run_id": "run_case01_001",
  "stage": "QA",
  "status": "PASS",
  "comsol_version": "6.3.0.290",
  "model_identity": {
    "entry": "runtime/Case01.java",
    "case_id": "case01",
    "parameters": {"temperature": "318.15[K]"}
  },
  "artifacts": [
    {"role": "model", "path": "model/case01.mph", "bytes_min": 100, "sha256": "填入64位SHA-256"},
    {"role": "raw_data", "path": "exports_raw/profile.csv", "bytes_min": 20, "sha256": "填入64位SHA-256"},
    {"role": "validation", "path": "report/validation.json", "bytes_min": 20, "sha256": "填入64位SHA-256"}
  ],
  "evidence": {
    "solve_authorized": true,
    "study_complete": true,
    "solution_identity_checked": true,
    "log_scan_pass": true,
    "model_identity_match": true,
    "units_checked": true,
    "physics_qa_pass": true,
    "scientific_scope_checked": true
  }
}
```

## Artifact roles

- `model`：保存的 MPH；
- `raw_data`：未经改写的 COMSOL 原始导出；
- `canonical_data`：带转换记录的标准化数据；
- `figure`：当前数据生成的图件；
- `log`：编译、批处理或会话日志；
- `validation`：机器与科学 QA 汇总；
- `source`：Java、Method、脚本或完整可重放输入。

同一角色可出现多次。到 `Save` 至少需要 `model`，到 `Export` 至少需要 `raw_data`，到 `QA` 还需要 `validation`；进入 `Promote` 还必须保留 `source`，避免正式结果脱离可复现入口。

`QA` 和 `Promote` 阶段只有在 `status` 明确为 `PASS` 时才可能通过校验。较早阶段可以使用 `PARTIAL` 表示尚未完成，但不能据此声称已经求解或通过科学 QA。

## 运行

```bash
python scripts/validate_run_evidence.py /absolute/path/to/runs/<run_id>
```

指定其他 manifest 或写出机器报告：

```bash
python scripts/validate_run_evidence.py /absolute/path/to/run \
  --manifest report/custom_manifest.json \
  --json-out report/evidence_check.json
```

退出码：`0` 通过，`1` 证据不闭合，`2` 输入或 JSON 无法读取。
