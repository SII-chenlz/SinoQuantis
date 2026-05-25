create table if not exists stock_basic (
    ts_code varchar,
    symbol varchar,
    name varchar,
    area varchar,
    industry varchar,
    market varchar,
    list_date date,
    delist_date date,
    source varchar,
    ingest_time timestamp,
    primary key (ts_code)
);

create table if not exists trade_calendar (
    exchange varchar,
    cal_date date,
    is_open boolean,
    pretrade_date date,
    source varchar,
    ingest_time timestamp,
    primary key (exchange, cal_date)
);

create table if not exists daily_bar (
    ts_code varchar,
    trade_date date,
    open double,
    high double,
    low double,
    close double,
    pre_close double,
    change double,
    pct_chg double,
    vol double,
    amount double,
    source varchar,
    ingest_time timestamp,
    primary key (ts_code, trade_date, source)
);

create table if not exists adj_factor (
    ts_code varchar,
    trade_date date,
    adj_factor double,
    source varchar,
    ingest_time timestamp,
    primary key (ts_code, trade_date, source)
);

create table if not exists financial_indicator (
    ts_code varchar,
    fiscal_period date,
    announcement_date date,
    eps double,
    roe double,
    roa double,
    gross_margin double,
    netprofit_margin double,
    debt_to_asset double,
    current_ratio double,
    source varchar,
    ingest_time timestamp,
    primary key (ts_code, fiscal_period, announcement_date, source)
);

create table if not exists financial_statement_long (
    ts_code varchar,
    report_type varchar,
    statement_type varchar,
    fiscal_period date,
    announcement_date date,
    account_name varchar,
    account_code varchar,
    value double,
    unit varchar,
    currency varchar,
    source varchar,
    ingest_time timestamp,
    version varchar,
    primary key (
        ts_code,
        statement_type,
        fiscal_period,
        announcement_date,
        account_code,
        source,
        version
    )
);

create table if not exists filing_index (
    source_doc_id varchar,
    ts_code varchar,
    company_name varchar,
    title varchar,
    filing_type varchar,
    report_period date,
    announcement_date date,
    url varchar,
    local_path varchar,
    source varchar,
    ingest_time timestamp,
    file_hash varchar,
    primary key (source_doc_id)
);

create table if not exists filing_text (
    source_doc_id varchar,
    ts_code varchar,
    title varchar,
    announcement_date date,
    text_content varchar,
    text_hash varchar,
    parser_version varchar,
    source varchar,
    ingest_time timestamp,
    primary key (source_doc_id, parser_version)
);

create table if not exists llm_analysis (
    analysis_id varchar,
    source_doc_id varchar,
    ts_code varchar,
    announcement_date date,
    prompt_version varchar,
    model varchar,
    input_hash varchar,
    output_json varchar,
    raw_output varchar,
    parse_status varchar,
    created_time timestamp,
    source varchar,
    ingest_time timestamp,
    primary key (analysis_id)
);

create table if not exists factor_value (
    ts_code varchar,
    trade_date date,
    factor_name varchar,
    factor_value double,
    source_table varchar,
    created_time timestamp,
    primary key (ts_code, trade_date, factor_name)
);

create table if not exists backtest_result (
    strategy_name varchar,
    start_date date,
    end_date date,
    initial_cash double,
    final_value double,
    annual_return double,
    max_drawdown double,
    sharpe double,
    turnover double,
    config_json varchar,
    created_time timestamp
);
