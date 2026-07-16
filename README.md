# 财务数据驾驶舱

一套可替换真实数据的 Streamlit 财务分析驾驶舱，包含：

- 经营总览
- 月度分析
- 季度分析
- 年度分析
- 预算与行业对标

## 数据文件

数据统一存放在 `data` 目录：

- `financial_monthly.csv`：公司月度财务数据
- `industry_benchmark_monthly.csv`：板块月度行业基准
- `metric_definitions.csv`：指标口径说明

替换真实数据时，请保持字段名称不变。金额单位统一为万元；利润表与现金流指标为当月发生额，资产负债表指标为月末余额。

## 本地运行

```powershell
python -m streamlit run app.py
```

## 重新生成模拟数据

```powershell
python generate_mock_data.py
```

## 全自动更新

将符合模板的数据文件放入 `待处理数据`，自动任务会校验、备份、更新 GitHub 并触发 Streamlit 重新部署。详见 `全自动更新说明.md`。
