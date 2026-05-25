# SinoQuantis

**SinoQuantis** 是一个面向 A 股的量化研究平台，目标是逐步建设“数据中台 + 因子研究 + 回测验证 + LLM 基本面分析”的可扩展系统。

当前阶段只做数据研究和回测准备，不接入实盘交易，不连接券商，不下真实订单，也不构成任何投资建议。

## 当前状态

已完成初始骨架和 Task 3：A 股数据源接入。

当前已支持：

- DuckDB 本地数据库 schema 初始化
- Tushare Pro 数据源适配器
- AKShare 免费研究数据源适配器
- 股票基础信息更新
- 交易日历更新
- 日线行情更新
- 复权因子更新
- 财务指标更新
- 巨潮公告索引更新
- CLI 命令入口
- 本地 Web 操作台
- mocked tests，避免测试依赖真实外部 API

暂未实现：

- DeepSeek API 分析模块
- 公告 PDF 下载和正文解析
- LLM 文本因子
- 因子生成
- 回测引擎
- Qlib 导出
- 实盘交易

## 设计原则

1. 数据层自己掌控，不把核心数据质量完全交给外部框架。
2. 财报、公告、LLM 分析结果都必须保留披露日期或可用日期。
3. 严格避免未来函数。
4. T 日信号只能从 T+1 开始交易。
5. LLM 只做文本结构化、风险提取和研究辅助，不直接给出买入/卖出建议。
6. 第一阶段只做研究和回测，不接入实盘。
7. 所有 API key 只能从环境变量读取，不能写死在代码里。
8. 外部 API 调用必须有异常处理和日志，单个数据源失败不能拖垮整个 pipeline。

## 安装

```bash
cd "/Users/chenlz/Sii/code/New project /sinoquantis"

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

如果网络较慢，且依赖已经在当前 Python 环境中，可以先用：

```bash
python -m pip install -e . --no-build-isolation
```

## 环境变量

复制示例配置：

```bash
cp .env.example .env
```

`.env` 中可配置：

```env
TUSHARE_TOKEN=
DEEPSEEK_API_KEY=
```

说明：

- `TUSHARE_TOKEN`：可选。没有 token 时，Tushare 数据源会被跳过，程序不会崩溃。
- `DEEPSEEK_API_KEY`：预留。当前 Task 3 不实现 DeepSeek，只保留后续扩展入口。

## 初始化和检查

```bash
python -m sinoquantis.cli doctor
python -m sinoquantis.cli init-db
```

`doctor` 会检查：

- Python 版本
- DuckDB 版本
- 数据目录
- 数据库路径
- `TUSHARE_TOKEN` 是否存在
- `DEEPSEEK_API_KEY` 是否存在

## 数据更新命令

更新股票基础信息：

```bash
python -m sinoquantis.cli update-stock-basic
```

更新交易日历：

```bash
python -m sinoquantis.cli update-calendar --start 20100101 --end 20261231
```

更新日线行情：

```bash
python -m sinoquantis.cli update-daily --start 20200101 --end 20260524
```

更新复权因子：

```bash
python -m sinoquantis.cli update-adj-factor --start 20200101 --end 20260524
```

更新财务指标：

```bash
python -m sinoquantis.cli update-financials --start 20180101 --end 20260524
```

更新公告索引：

```bash
python -m sinoquantis.cli update-filings --start 20240101 --end 20260524
```

## 数据源策略

### Tushare Pro

优先用于：

- 股票基础信息
- 交易日历
- 日线行情
- 复权因子
- 财务指标

要求：

- token 从 `TUSHARE_TOKEN` 读取。
- 没有 token 时只记录 warning 并跳过。
- 接口失败时记录日志，不让整个 pipeline 崩溃。

### AKShare

作为免费研究数据源和 fallback，用于：

- 股票代码/名称补充
- 日线行情补充
- 部分财务指标补充

AKShare 接口可能变化，所以所有调用都封装在 `data_sources/akshare_client.py`，后续替换时不影响上层 pipeline。

## 数据库

默认数据库路径：

```text
data/quant.duckdb
```

核心表包括：

- `stock_basic`
- `trade_calendar`
- `daily_bar`
- `adj_factor`
- `financial_indicator`
- `financial_statement_long`
- `filing_index`
- `filing_text`
- `llm_analysis`
- `factor_value`
- `backtest_result`

写入策略：

- 使用 delete + insert 的 upsert 方式。
- 避免重复写入。
- 大批量数据预留按日期或股票代码分批更新能力。


## Web 操作台

可以启动一个本地 Web 控制台，用浏览器执行常用量化数据操作：

```bash
python -m sinoquantis.cli serve-web --host 127.0.0.1 --port 8765
```

然后打开：

```text
http://127.0.0.1:8765
```

当前 Web 控制台支持：

- 查看环境状态
- 查看核心数据表是否存在和行数
- 初始化数据库
- 更新股票基础信息
- 按日期区间更新交易日历、日线行情、复权因子、财务指标、公告索引

说明：第一版 Web 操作台使用 Python 标准库实现，不依赖复杂前端框架。大范围数据更新可能耗时较长，建议先用较小日期区间试跑。

## 测试和代码质量

运行测试：

```bash
pytest
```

运行 ruff：

```bash
python -m ruff check .
```

当前测试覆盖：

- 数据库 schema 初始化
- CLI `doctor` smoke test
- Tushare token 缺失时的 AKShare fallback
- 交易日历更新
- 日线行情按股票代码批量 fallback
- 财务数据丢弃缺失 `announcement_date` 的记录

## 路线图

- Task 1：项目骨架
- Task 2：DuckDB schema 和存储工具
- Task 3：Tushare + AKShare 数据源接入，已完成
- Task 4：公告索引、PDF 下载预留、公告正文解析入口，部分完成
- Task 5：DeepSeek API 分析模块
- Task 6：基础因子生成
- Task 7：日频回测引擎
- Task 8：LLM 文本因子和组合策略
- Task 9：Qlib 数据导出
- Task 10：研究报告生成

## 风险提示

SinoQuantis 仅用于研究和教学，不构成投资建议。外部数据源可能存在缺失、延迟、字段变化或质量问题。任何回测结果都不代表未来收益。第一阶段不接入实盘交易，不下真实订单。
