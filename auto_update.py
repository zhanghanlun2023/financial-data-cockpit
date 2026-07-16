from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from tb_parser import parse_tb


ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "待处理数据"
PROCESSED = ROOT / "已处理"
FAILED = ROOT / "处理失败"
BACKUP = ROOT / "备份"
LOG_DIR = ROOT / "日志"
DATA_DIR = ROOT / "data"
LOCK_FILE = ROOT / ".auto_update.lock"

FINANCIAL_TARGET = DATA_DIR / "financial_monthly.csv"
BENCHMARK_TARGET = DATA_DIR / "industry_benchmark_monthly.csv"
FINANCIAL_TEMPLATE = ROOT / "财务月度数据模板.xlsx"
BENCHMARK_TEMPLATE = ROOT / "行业对标数据模板.xlsx"

FINANCIAL_VALUE_COLUMNS = [
    "营业收入",
    "营业成本",
    "销售费用",
    "管理费用",
    "研发费用",
    "财务费用",
    "其他收益",
    "利润总额",
    "净利润",
    "经营活动现金流",
    "预算营业收入",
    "预算利润总额",
    "应收账款",
    "存货",
    "资产总额",
    "负债总额",
    "所有者权益",
]

FINANCIAL_REQUIRED = ["日期", "公司", "板块", *FINANCIAL_VALUE_COLUMNS]
BENCHMARK_VALUE_COLUMNS = [
    "行业营业收入中位数",
    "行业利润率中位数",
    "行业现金质量中位数",
    "行业资产负债率中位数",
]
BENCHMARK_REQUIRED = ["日期", "板块", *BENCHMARK_VALUE_COLUMNS]

HEADER_ALIASES = {
    "会计期间": "日期",
    "年月": "日期",
    "期间": "日期",
    "单位名称": "公司",
    "组织名称": "公司",
    "公司名称": "公司",
    "业务板块": "板块",
    "经营活动产生的现金流量净额": "经营活动现金流",
    "经营现金流": "经营活动现金流",
    "收入预算": "预算营业收入",
    "利润预算": "预算利润总额",
    "总资产": "资产总额",
    "总负债": "负债总额",
    "净资产": "所有者权益",
}


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_directories() -> None:
    for folder in [INBOX, PROCESSED, FAILED, BACKUP, LOG_DIR, DATA_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def write_log(level: str, message: str, **details: object) -> None:
    ensure_directories()
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "message": message,
        **details,
    }
    log_file = LOG_DIR / f"自动更新_{datetime.now():%Y%m}.jsonl"
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False))


def acquire_lock() -> int | None:
    try:
        return os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None


def release_lock(lock_fd: int) -> None:
    os.close(lock_fd)
    LOCK_FILE.unlink(missing_ok=True)


def read_tabular(path: Path, kind: str) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="gb18030")
    if suffix in {".xlsx", ".xlsm"}:
        sheets = pd.read_excel(path, sheet_name=None)
        candidates = [frame for frame in sheets.values() if not frame.empty]
        if not candidates:
            raise ValueError("Excel 中没有可读取的数据工作表")
        expected = FINANCIAL_REQUIRED if kind == "financial" else BENCHMARK_REQUIRED
        ranked = sorted(candidates, key=lambda frame: len(set(map(str, frame.columns)) & set(expected)), reverse=True)
        return ranked[0]
    raise ValueError(f"不支持的文件格式：{suffix}，仅支持 CSV、XLSX、XLSM")


def normalize_headers(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.columns = [str(column).strip().replace("\n", "") for column in result.columns]
    result = result.rename(columns={column: HEADER_ALIASES.get(column, column) for column in result.columns})
    return result


def normalize_dates(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip().str.replace("年", "-", regex=False).str.replace("月", "", regex=False)
    parsed = pd.to_datetime(text, errors="coerce")
    return parsed.dt.to_period("M").dt.to_timestamp()


def clean_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        cleaned = (
            result[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("，", "", regex=False)
            .str.replace("万元", "", regex=False)
            .str.strip()
            .replace({"": None, "nan": None, "None": None, "—": None, "-": None})
        )
        result[column] = pd.to_numeric(cleaned, errors="coerce")
    return result


def validate_financial(frame: pd.DataFrame) -> pd.DataFrame:
    result = normalize_headers(frame)
    missing = [column for column in FINANCIAL_REQUIRED if column not in result.columns]
    if missing:
        raise ValueError("缺少财务字段：" + "、".join(missing))
    result = result[FINANCIAL_REQUIRED].copy()
    result["日期"] = normalize_dates(result["日期"])
    result["公司"] = result["公司"].astype(str).str.strip()
    result["板块"] = result["板块"].astype(str).str.strip()
    result = clean_numeric(result, FINANCIAL_VALUE_COLUMNS)
    if result["日期"].isna().any():
        raise ValueError(f"存在 {int(result['日期'].isna().sum())} 行无法识别的日期")
    null_counts = result[FINANCIAL_VALUE_COLUMNS].isna().sum()
    invalid = null_counts[null_counts > 0]
    if not invalid.empty:
        raise ValueError("关键金额存在空值：" + "、".join(f"{name}({count}行)" for name, count in invalid.items()))
    if (result["公司"] == "").any() or (result["板块"] == "").any():
        raise ValueError("公司或板块名称不能为空")
    duplicates = result.duplicated(["日期", "公司"], keep=False)
    if duplicates.any():
        raise ValueError(f"日期+公司存在 {int(duplicates.sum())} 行重复记录")
    if (result[["营业收入", "资产总额", "所有者权益"]] < 0).any().any():
        raise ValueError("营业收入、资产总额或所有者权益不能为负数")
    if (result["负债总额"] > result["资产总额"] * 1.2).any():
        raise ValueError("存在负债总额显著高于资产总额的异常记录")
    result.insert(1, "年度", result["日期"].dt.year)
    result.insert(2, "月份", result["日期"].dt.month)
    result.insert(3, "季度", "Q" + (((result["日期"].dt.month - 1) // 3) + 1).astype(str))
    result["日期"] = result["日期"].dt.strftime("%Y-%m-%d")
    return result.sort_values(["日期", "公司"]).reset_index(drop=True)


def validate_benchmark(frame: pd.DataFrame) -> pd.DataFrame:
    result = normalize_headers(frame)
    missing = [column for column in BENCHMARK_REQUIRED if column not in result.columns]
    if missing:
        raise ValueError("缺少行业对标字段：" + "、".join(missing))
    result = result[BENCHMARK_REQUIRED].copy()
    result["日期"] = normalize_dates(result["日期"])
    result["板块"] = result["板块"].astype(str).str.strip()
    result = clean_numeric(result, BENCHMARK_VALUE_COLUMNS)
    if result["日期"].isna().any() or result[BENCHMARK_VALUE_COLUMNS].isna().any().any():
        raise ValueError("行业对标数据存在无法识别的日期或空值")
    duplicates = result.duplicated(["日期", "板块"], keep=False)
    if duplicates.any():
        raise ValueError(f"日期+板块存在 {int(duplicates.sum())} 行重复记录")
    ratio_columns = ["行业利润率中位数", "行业资产负债率中位数"]
    for column in ratio_columns:
        if result[column].abs().max() > 2:
            result[column] = result[column] / 100
    result.insert(1, "年度", result["日期"].dt.year)
    result.insert(2, "月份", result["日期"].dt.month)
    result.insert(3, "季度", "Q" + (((result["日期"].dt.month - 1) // 3) + 1).astype(str))
    result["日期"] = result["日期"].dt.strftime("%Y-%m-%d")
    return result.sort_values(["日期", "板块"]).reset_index(drop=True)


def file_kind(path: Path) -> str:
    lowered = path.name.lower()
    return "benchmark" if any(word in lowered for word in ["benchmark", "行业", "对标", "基准"]) else "financial"


def backup_target(target: Path) -> None:
    if target.exists():
        destination = BACKUP / f"{now_stamp()}_{target.name}"
        shutil.copy2(target, destination)


def install_dataset(source: Path) -> list[Path]:
    if "tb" in source.name.lower() and source.suffix.lower() == ".xls":
        targets = [DATA_DIR / "tb_detail.csv", DATA_DIR / "tb_summary.csv", DATA_DIR / "tb_quality.json"]
        for target in targets:
            backup_target(target)
        detail, summary, audit = parse_tb(source)
        detail.to_csv(targets[0], index=False, encoding="utf-8-sig")
        summary.to_csv(targets[1], index=False, encoding="utf-8-sig")
        targets[2].write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        return targets
    kind = file_kind(source)
    frame = read_tabular(source, kind)
    if kind == "benchmark":
        validated = validate_benchmark(frame)
        target = BENCHMARK_TARGET
    else:
        validated = validate_financial(frame)
        target = FINANCIAL_TARGET
    backup_target(target)
    temporary = target.with_suffix(target.suffix + ".tmp")
    validated.to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(target)
    return [target]


def run_git_publish(changed_targets: list[Path]) -> str:
    relative_targets = [str(path.relative_to(ROOT)).replace("\\", "/") for path in changed_targets]
    subprocess.run(["git", "add", "--", *relative_targets], cwd=ROOT, check=True, capture_output=True, text=True)
    status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if status.returncode == 0:
        return "数据与 GitHub 已一致，无需提交"
    message = f"Auto update financial dashboard data {datetime.now():%Y-%m-%d %H:%M}"
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True, capture_output=True, text=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True, capture_output=True, text=True)
    return message


def move_with_stamp(source: Path, destination_folder: Path) -> Path:
    destination = destination_folder / f"{now_stamp()}_{source.name}"
    shutil.move(str(source), destination)
    return destination


def process_inbox(publish: bool = True) -> int:
    ensure_directories()
    files = sorted(
        [path for path in INBOX.iterdir() if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xlsm", ".xls"}],
        key=lambda path: path.stat().st_mtime,
    )
    if not files:
        write_log("INFO", "未发现待处理数据")
        return 0

    changed_targets: list[Path] = []
    success_count = 0
    for source in files:
        try:
            targets = install_dataset(source)
            changed_targets.extend(targets)
            processed_path = move_with_stamp(source, PROCESSED)
            success_count += 1
            write_log("SUCCESS", "数据校验并安装成功", source=source.name, targets=[x.name for x in targets], archived=str(processed_path))
        except Exception as exc:
            failed_path = move_with_stamp(source, FAILED)
            write_log("ERROR", "数据处理失败，线上数据未更新", source=source.name, error=str(exc), archived=str(failed_path))

    if changed_targets and publish:
        try:
            message = run_git_publish(sorted(set(changed_targets)))
            write_log("SUCCESS", "GitHub 推送完成，Streamlit 将自动重新部署", commit=message)
        except Exception as exc:
            write_log("ERROR", "本地数据已更新，但 GitHub 推送失败", error=str(exc))
            return 2
    return 0 if success_count else 1


def create_template() -> None:
    ensure_directories()
    financial = pd.read_csv(FINANCIAL_TARGET, encoding="utf-8-sig") if FINANCIAL_TARGET.exists() else pd.DataFrame(columns=FINANCIAL_REQUIRED)
    benchmark = pd.read_csv(BENCHMARK_TARGET, encoding="utf-8-sig") if BENCHMARK_TARGET.exists() else pd.DataFrame(columns=BENCHMARK_REQUIRED)
    with pd.ExcelWriter(FINANCIAL_TEMPLATE, engine="openpyxl") as writer:
        financial.to_excel(writer, sheet_name="财务月度数据", index=False)
    with pd.ExcelWriter(BENCHMARK_TEMPLATE, engine="openpyxl") as writer:
        benchmark.to_excel(writer, sheet_name="行业对标数据", index=False)
    write_log("SUCCESS", "目录和数据模板已初始化", financial_template=str(FINANCIAL_TEMPLATE), benchmark_template=str(BENCHMARK_TEMPLATE))


def main() -> int:
    parser = argparse.ArgumentParser(description="财务驾驶舱自动数据更新")
    parser.add_argument("--init", action="store_true", help="创建目录和 Excel 数据模板")
    parser.add_argument("--no-publish", action="store_true", help="只更新本地数据，不推送 GitHub")
    args = parser.parse_args()
    ensure_directories()
    if args.init:
        create_template()
        return 0
    lock_fd = acquire_lock()
    if lock_fd is None:
        write_log("INFO", "另一个自动更新任务正在运行，本次跳过")
        return 0
    try:
        return process_inbox(publish=not args.no_publish)
    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    sys.exit(main())
