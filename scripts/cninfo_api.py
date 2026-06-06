"""
深证信数据服务平台 (CNINFO) API 工具模块
===========================================
官方一手 A 股数据源（深交所子公司运营），免费 tier 可用。

认证: 使用 web 前端的 mcode 加密机制 (Accept-Enckey 头)，
      无需 OAuth2 token（OAuth2 仅限 VIP 接口）。

已封装端点 (11个):
  p_stock2303    财务指标 (143字段)
  p_stock2334    TTM主要财务指标
  p_sysapi1133   公司概况
  p_info3097_inc 个股研报摘要
  p_stock2205    投资评级+目标价
  p_sysapi1087   行业PE
  p_sysapi1139   分红数据
  p_sysapi1029   股东户数
  p_stock2215    股本变动
  p_stock2110    行业分类 (8套标准)
  p_sysapi1134   IPO概况

用法:
    from scripts.cninfo_api import CninfoClient
    client = CninfoClient()

    # 财务分析
    df = client.financial_multi_year("600519", years=[2020,2021,2022,2023,2024])
    ttm = client.ttm_indicators("600519")  # 最新TTM

    # 估值锚点
    ratings = client.investment_ratings("600519")      # 投资评级+目标价
    pe = client.industry_pe("600519")                  # 行业PE对比
    reports = client.research_reports("600519")        # 研报摘要

    # 质量验证
    div = client.dividends("600519")                   # 分红历史
    holders = client.shareholder_structure("600519")   # 股东户数趋势
    changes = client.share_changes("600519")           # 股本变动
    ipo = client.ipo_summary("600519")                 # IPO概况
"""

import requests
import py_mini_racer
import pandas as pd
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# mcode 生成
# ══════════════════════════════════════════════════════════════

_JS_CODE = None

def _get_js_code():
    global _JS_CODE
    if _JS_CODE is None:
        import akshare.datasets as ds
        _JS_CODE = Path(ds.get_ths_js("cninfo.js")).read_text(encoding="utf-8")
    return _JS_CODE

def _gen_mcode():
    js_engine = py_mini_racer.MiniRacer()
    js_engine.eval(_get_js_code())
    return js_engine.call("getResCode1")

# ══════════════════════════════════════════════════════════════
# 字段名映射
# ══════════════════════════════════════════════════════════════

# ── p_stock2303 个股报告期财务指标 (143字段) ──

FINANCIAL_FIELD_MAP = {
    "F001V": "数据来源编码", "F002V": "数据来源",
    "F003N": "每股收益(元)", "F004N": "基本每股收益(元)", "F005N": "稀释每股收益(元)",
    "F006N": "扣非每股收益(元)", "F007N": "每股未分配利润(元)", "F008N": "每股净资产(元)",
    "F009N": "调整后每股净资产(元)", "F010N": "每股资本公积金(元)",
    "F011N": "营业利润率(%)", "F012N": "营业税金率(%)", "F013N": "营业成本率(%)",
    "F014N": "净资产收益率(%)", "F015N": "投资收益率(%)", "F016N": "总资产报酬率(%)",
    "F017N": "净利润率(%)", "F018N": "管理费用率(%)", "F019N": "财务费用率(%)",
    "F020N": "成本费用利润率(%)", "F021N": "三费比重(%)",
    "F022N": "应收账款周转率(次)", "F023N": "存货周转率(次)", "F024N": "运营资金周转率(次)",
    "F025N": "总资产周转率(次)", "F026N": "固定资产周转率(次)",
    "F027N": "应收账款周转天数", "F028N": "存货周转天数",
    "F029N": "流动资产周转率(次)", "F030N": "流动资产周转天数", "F031N": "总资产周转天数",
    "F032N": "股东权益周转率(次)",
    "F033N": "流动资产比率(%)", "F034N": "货币资金比率(%)", "F035N": "交易性金融资产比率(%)",
    "F036N": "存货比率(%)", "F037N": "固定资产比率(%)", "F038N": "负债结构比(%)",
    "F039N": "产权比率(%)", "F040N": "净资产比率(%)", "F041N": "资产负债比率(%)",
    "F042N": "流动比率", "F043N": "速动比率", "F044N": "现金比率(%)",
    "F045N": "利息保障倍数", "F046N": "营运资金(元)",
    "F047N": "非流动负债比率(%)", "F048N": "流动负债比率(%)", "F049N": "保守速动比率",
    "F050N": "现金到期债务比率(%)", "F051N": "有形资产净值债务率(%)",
    "F052N": "营业收入增长率(%)", "F053N": "净利润增长率(%)",
    "F054N": "净资产增长率(%)", "F055N": "固定资产增长率(%)", "F056N": "总资产增长率(%)",
    "F057N": "投资收益增长率(%)", "F058N": "营业利润增长率(%)",
    "F059N": "每股现金流量(元)", "F060N": "每股经营现金流量(元)",
    "F061N": "经营净现金比率(短期债务)(%)", "F062N": "经营净现金比率(全部债务)(%)",
    "F063N": "经营活动现金净流量与净利润比率(%)", "F064N": "营业收入现金含量(%)",
    "F065N": "全部资产现金回收率(%)",
    "F066N": "净资产收益率(扣非)(%)", "F067N": "净资产收益率(加权)(%)",
    "F068N": "净资产收益率(加权扣非)(%)",
    "F069D": "报告年度", "F070V": "合并类型编码", "F071V": "合并类型",
    "F076N": "扣非净利润(元)", "F077N": "非经常性损益合计(元)",
    "F078N": "毛利率(%)", "F079N": "期间费用率(%)", "F080N": "现金转换周期(天)",
    "F081N": "净资产收益率(年末,%)", "F082N": "净利含金量", "F083N": "非经常性损益占比(%)",
    "F084N": "期间费用增长率(%)", "F085N": "基本获利能力(EBIT)(元)",
    "F086N": "应收账款占比(%)", "F087N": "存货占比(%)", "F088N": "年化期间费用毛利比(%)",
    "F089N": "营业收入(元)", "F090N": "营业成本(元)",
    "F091N": "销售费用(元)", "F092N": "管理费用(元)", "F093N": "财务费用(元)",
    "F094N": "三费合计(元)", "F095N": "公允价值变动净收益(元)", "F096N": "投资收益(元)",
    "F097N": "营业利润(元)", "F098N": "补贴收入(元)", "F099N": "营业外收支净额(元)",
    "F100N": "利润总额(元)", "F101N": "净利润(元)",
    "F102N": "归母净利润(元)", "F103N": "扣非净利润(2007版)(元)",
    "F104N": "非经常性损益合计(2007版)(元)",
    "F105N": "经营活动现金流量净额(元)", "F106N": "投资活动现金流量净额(元)",
    "F107N": "筹资活动现金流量净额(元)", "F108N": "现金及现金等价物净增加额(元)",
    "F109N": "货币资金(元)", "F110N": "交易性金融资产(元)", "F111N": "应收账款(元)",
    "F112N": "存货(元)", "F113N": "流动资产合计(元)",
    "F114N": "投资性房地产(元)", "F115N": "商誉(元)", "F116N": "固定资产(元)",
    "F117N": "非流动资产合计(元)", "F118N": "资产总计(元)",
    "F119N": "流动负债合计(元)", "F120N": "非流动负债合计(元)", "F121N": "负债合计(元)",
    "F122N": "股本(元)", "F123N": "资本公积(元)", "F124N": "盈余公积(元)",
    "F125N": "库存股(元)", "F126N": "未分配利润(元)", "F127N": "少数股东权益(元)",
    "F128N": "股东权益合计(元)", "F129N": "归母所有者权益(元)",
    "F130N": "研发费用(元)", "F131N": "研发费用率(%)", "F132N": "销售费用率(%)",
    "F133N": "四费费用率(%)", "F134N": "四费费用率同比变化值(%)",
    "F135N": "三费费用率同比变化值(%)", "F136N": "财务费用率同比变化值(%)",
    "F137N": "管理费用率同比变化值(%)", "F138N": "销售费用率同比变化值(%)",
    "F139N": "研发费用率同比变化值(%)", "F140N": "毛利率同比变化值(%)",
    "F141N": "扣非净利润同比变化率(%)", "F142N": "归母净利润同比变化率(%)",
    "F143N": "经营现金流净额同比变化率(%)",
}

# ── p_stock2100_inc 公司基本信息 ──

COMPANY_BASIC_FIELD_MAP = {
    "ORGNAME": "机构名称", "SECCODE": "证券代码", "SECNAME": "证券简称",
    "F001V": "英文名称", "F002V": "英文简称", "F003V": "法人代表",
    "F004V": "注册地址", "F005V": "办公地址", "F006V": "邮政编码",
    "F007N": "注册资金", "F008V": "货币编码", "F009V": "货币名称",
    "F010D": "成立日期", "F011V": "机构网址", "F012V": "电子信箱",
    "F013V": "联系电话", "F014V": "联系传真",
    "F015V": "主营业务", "F016V": "经营范围", "F017V": "机构简介",
    "F018V": "董事会秘书", "F019V": "董秘联系电话", "F020V": "董秘联系传真",
    "F021V": "董秘电子邮箱", "F022V": "证券事务代表",
    "F023V": "上市状态编码", "F024V": "上市状态",
    "F025V": "所属省份编码", "F026V": "所属省份",
    "F027V": "所属城市编码", "F028V": "所属城市",
    "F029V": "中上协一级行业编码", "F030V": "中上协一级行业名称",
    "F031V": "中上协二级行业编码", "F032V": "中上协二级行业名称",
    "F033V": "申万一级行业编码", "F034V": "申万一级行业名称",
    "F035V": "申万二级行业编码", "F036V": "申万二级行业名称",
    "F037V": "申万三级行业编码", "F038V": "申万三级行业名称",
    "F039V": "会计师事务所", "F040V": "律师事务所",
    "F041V": "董事长", "F042V": "总经理", "F043V": "独立董事",
    "F044V": "入选指数", "F045V": "最新报告预约日期",
    "F046V": "保荐机构", "F047V": "主承销商", "F048V": "PEVC标记",
    "F049V": "注册国家", "F050V": "统一社会信用代码", "F051V": "工商ID",
    "F052V": "可转债", "F053V": "CDR",
}

# ── p_stock2334 TTM主要财务指标 ──

TTM_FIELD_MAP = {
    "F001D": "报告年度", "F002V": "合并类型编码", "F003V": "合并类型",
    "F006N": "基本每股收益(元)", "F007N": "每股未分配利润(元)",
    "F008N": "营业利润率(%)", "F009N": "营业税金率(%)", "F010N": "营业成本率(%)",
    "F011N": "净资产收益率(%)", "F012N": "投资收益率(%)", "F013N": "总资产报酬率(%)",
    "F014N": "净利润率(%)", "F015N": "管理费用率(%)", "F016N": "财务费用率(%)",
    "F017N": "成本费用利润率(%)", "F018N": "三费比重(%)",
    "F019N": "应收账款周转率(次)", "F020N": "存货周转率(次)",
    "F021N": "运营资金周转率(次)", "F022N": "总资产周转率(次)", "F023N": "固定资产周转率(次)",
    "F024N": "应收账款周转天数", "F025N": "存货周转天数",
    "F026N": "流动资产周转率(次)", "F027N": "流动资产周转天数", "F028N": "总资产周转天数",
    "F029N": "股东权益周转率(次)", "F030N": "利息保障倍数",
    "F031N": "营业收入增长率(%)", "F032N": "净利润增长率(%)",
    "F033N": "净资产增长率(%)", "F034N": "固定资产增长率(%)", "F035N": "总资产增长率(%)",
    "F036N": "投资收益增长率(%)", "F037N": "营业利润增长率(%)",
    "F038N": "每股现金流量(元)", "F039N": "每股经营现金流量(元)",
    "F040N": "经营净现金比率(短期债务)(%)", "F041N": "经营净现金比率(全部债务)(%)",
    "F042N": "经营现金流/净利润(%)", "F043N": "营业收入现金含量(%)",
    "F044N": "全部资产现金回收率(%)",
    "F045N": "毛利率(%)", "F046N": "期间费用率(%)", "F047N": "现金转换周期(天)",
    "F048N": "净利含金量", "F049N": "期间费用增长率(%)",
    "F050N": "基本获利能力(EBIT)(元)", "F051N": "应收账款占比(%)", "F052N": "存货占比(%)",
    "F053N": "年化期间费用毛利比(%)",
}

# ── p_stock2205 投资评级 ──

RATING_FIELD_MAP = {
    "DECLAREDATE": "发布日期", "F002V": "研究机构", "F003V": "研究员",
    "F004V": "投资评级", "F005V": "投资评级(调整后)", "F006V": "是否首次评级",
    "F007V": "评级变化", "F008V": "前次评级",
    "F009N": "目标价下限(元)", "F010N": "目标价上限(元)",
}

# ── p_sysapi1139 分红数据 ──

DIVIDEND_FIELD_MAP = {
    "F001V": "分红年度", "F007V": "分红方案",
    "F012N": "每股分红(元)", "F006D": "股权登记日", "F023D": "除权除息日",
    "F018D": "公告日期", "F020D": "发放日期", "F044V": "分红类型",
}

# ── p_sysapi1087 行业PE ──

INDUSTRY_PE_FIELD_MAP = {
    "VARYDATE": "数据日期", "F003V": "行业分类标准",
    "F005V": "行业编码", "F006V": "行业名称",
    "F007N": "公司数量", "F008N": "盈利公司数",
    "F009N": "总市值(亿)", "F010N": "净利润合计(亿)",
    "F011N": "加权PE", "F012N": "等权PE", "F013N": "中位数PE",
}

# ── p_sysapi1134 IPO概况 ──

IPO_FIELD_MAP = {
    "F003N": "发行股数(万股)", "F006D": "上市日期", "F007N": "每股面值(元)",
    "F008N": "发行价格(元)", "F013N": "发行市盈率(倍)", "F014N": "发行后每股收益(元)",
    "F015N": "发行后每股净资产(元)", "F028N": "募集资金净额(万元)",
    "F030N": "发行费用(万元)", "F034D": "发行公告日",
    "F035D": "中签率公告日", "F047V": "主承销商",
    "F050N": "发行市净率(倍)", "F109D": "转板日期",
}

# ── p_stock2110 行业分类 ──

INDUSTRY_CLASS_FIELD_MAP = {
    "VARYDATE": "分类日期", "F001V": "行业标准编码", "F002V": "行业标准名称",
    "F003V": "行业编码", "F004V": "门类", "F005V": "大类",
    "F006V": "中类", "F007V": "小类",
}

# ── p_sysapi1029 股东户数 ──

SHAREHOLDER_FIELD_MAP = {
    "VARYDATE": "截止日期", "DECLAREDATE": "公告日期",
    "F002V": "报表类型", "F003N": "股东户数", "F004N": "股东户数(上期)",
    "F005N": "户均持股(股)", "F006N": "户均持股市值(万元)",
    "MARKET": "所属市场",
}

# ── p_stock2215 股本变动 ──

SHARE_CHANGE_FIELD_MAP = {
    "VARYDATE": "变动日期", "DECLAREDATE": "公告日期",
    "F002V": "变动原因", "F003N": "总股本(万股)", "F004N": "流通A股(万股)",
    "F005N": "限售A股(万股)", "F008N": "已上市流通股(万股)",
}

# ── p_stock2329 单季财务利润表 ──

INCOME_STATEMENT_FIELD_MAP = {
    "F001D": "报告年度", "F002V": "合并类型编码", "F003V": "合并类型",
    "F006N": "营业收入(元)", "F007N": "营业成本(元)", "F008N": "营业税金及附加(元)",
    "F009N": "销售费用(元)", "F010N": "管理费用(元)", "F011N": "堪探费用(元)",
    "F012N": "财务费用(元)", "F013N": "资产减值损失(元)",
    "F014N": "公允价值变动净收益(元)", "F015N": "投资收益(元)",
    "F016N": "对联营企业和合营企业的投资收益(元)", "F017N": "影响营业利润的其他科目(元)",
    "F018N": "营业利润(元)", "F019N": "补贴收入(元)", "F020N": "营业外收入(元)",
    "F021N": "营业外支出(元)", "F022N": "非流动资产处置损失(元)",
    "F023N": "影响利润总额的其他科目(元)", "F024N": "利润总额(元)",
    "F025N": "所得税(元)", "F026N": "影响净利润的其他科目(元)",
    "F027N": "净利润(元)", "F028N": "归母净利润(元)", "F029N": "少数股东损益(元)",
    "F030N": "每股收益(元)", "F031N": "基本每股收益(元)",
    "F033N": "利息收入(元)", "F034N": "已赚保费(元)",
    "F035N": "营业总收入(元)", "F036N": "营业总成本(元)", "F037N": "汇兑收益(元)",
    "F038N": "其他综合收益(元)", "F039N": "综合收益总额(元)",
    "F040N": "归母综合收益(元)", "F041N": "少数股东综合收益(元)",
    "F042N": "手续费及佣金收入(元)", "F043N": "利息支出(元)",
    "F044N": "手续费及佣金支出(元)", "F045N": "退保金(元)",
    "F046N": "赔付支出净额(元)", "F047N": "提取保险合同准备金净额(元)",
    "F048N": "保单红利支出(元)", "F049N": "分保费用(元)",
    "F050N": "非流动资产处置利得(元)", "F051N": "其他收益(元)",
    "F052N": "研发费用(元)",
}

# ── p_stock2330 单季现金流量表 ──

CASHFLOW_STATEMENT_FIELD_MAP = {
    "F001D": "报告年度", "F002V": "合并类型编码", "F003V": "合并类型",
    "F006N": "销售商品提供劳务收到的现金(元)", "F007N": "收到的税费返还(元)",
    "F008N": "收到其他与经营活动有关的现金(元)", "F009N": "经营活动现金流入小计(元)",
    "F010N": "购买商品接受劳务支付的现金(元)", "F011N": "支付给职工以及为职工支付的现金(元)",
    "F012N": "支付的各项税费(元)", "F013N": "支付其他与经营活动有关的现金(元)",
    "F014N": "经营活动现金流出小计(元)", "F015N": "经营活动现金流量净额(元)",
    "F016N": "收回投资收到的现金(元)", "F017N": "取得投资收益收到的现金(元)",
    "F018N": "处置固定资产无形资产和其他长期资产收回的现金净额(元)",
    "F019N": "处置子公司及其他营业单位收到的现金净额(元)",
    "F020N": "收到其他与投资活动有关的现金(元)", "F021N": "投资活动现金流入小计(元)",
    "F022N": "购建固定资产无形资产和其他长期资产支付的现金(元)",
    "F023N": "投资支付的现金(元)", "F024N": "取得子公司及其他营业单位支付的现金净额(元)",
    "F025N": "支付其他与投资活动有关的现金(元)", "F026N": "投资活动现金流出小计(元)",
    "F027N": "投资活动现金流量净额(元)",
    "F028N": "吸收投资收到的现金(元)", "F029N": "取得借款收到的现金(元)",
    "F030N": "收到其他与筹资活动有关的现金(元)", "F031N": "筹资活动现金流入小计(元)",
    "F032N": "偿还债务支付的现金(元)", "F033N": "分配股利利润或偿付利息支付的现金(元)",
    "F034N": "支付其他与筹资活动有关的现金(元)", "F035N": "筹资活动现金流出小计(元)",
    "F036N": "筹资活动现金流量净额(元)",
    "F037N": "汇率变动对现金的影响(元)", "F038N": "其他原因对现金的影响(元)",
    "F039N": "现金及现金等价物净增加额(元)",
    "F040N": "期初现金及现金等价物余额(元)", "F041N": "期末现金及现金等价物余额(元)",
    "F044N": "净利润(元)", "F060N": "经营活动现金流量净额(间接法)(元)",
}

# ── p_info3097_inc 研报摘要 ──

RESEARCH_REPORT_FIELD_MAP = {
    "F001D": "资讯发布日期", "F002V": "资讯标题", "F003V": "资讯内容",
    "F004V": "研报发布机构", "F005D": "研报发布日期",
    "F007V": "资讯分类", "F009V": "证券类别", "F011V": "证券市场",
}

# ── p_stock2238 业绩预告 ──

FORECAST_FIELD_MAP = {
    "DECLAREDATE": "公告日期", "F001D": "报告年度",
    "F002V": "业绩类型编码", "F003V": "业绩类型",
    "F004V": "业绩预告内容", "F005V": "业绩变化原因",
    "F006C": "最新记录标识",
    "F007N": "净利润下限(元)", "F008N": "净利润上限(元)",
    "F009N": "净利润增减幅下限(%)", "F010N": "净利润增减幅上限(%)",
}

# ── p_stock2328 业绩快报 ──

EXPRESS_FIELD_MAP = {
    "DECLAREDATE": "公告日期", "STARTDATE": "开始日期", "ENDDATE": "截止日期",
    "F001V": "报表来源编码", "F002V": "报表来源",
    "F003N": "净利润(元)", "F004N": "总资产(元)",
    "F005N": "股东权益(元)", "F006N": "每股收益(元)",
    "F007N": "净资产收益率(%)", "F008N": "净资产收益率(加权)(%)",
    "F009N": "每股净资产(元)", "MEMO": "备注",
}

# ── p_stock2209 十大流通股东 ──

TOP10_HOLDER_FIELD_MAP = {
    "ORGNAME": "机构名称", "DECLAREDATE": "公告日期", "ENDDATE": "截止日期",
    "F001N": "股东名次", "F002V": "股东ID", "F003V": "股东名称",
    "F004V": "股东类别", "F005N": "持股数量(股)",
    "F006N": "占总股本比例(%)", "F007N": "占流通股本比例(%)",
    "F011V": "股份性质", "F012N": "持有B股(股)", "F013N": "持有H股(股)",
}

# ── p_stock2218 高管持股变动 ──

EXEC_TRADE_FIELD_MAP = {
    "ORGNAME": "机构名称", "DECLAREDATE": "公告日期", "ENDDATE": "截止日期",
    "HUMANNAME": "变动人", "F001V": "董监高姓名", "F002V": "董监高职务",
    "F003V": "变动人与董监高关系", "F004N": "期初持股(股)", "F005N": "期末持股(股)",
    "F006N": "变动数量(股)", "F007N": "变动比例(‰)", "F008N": "成交均价(元)",
    "F009N": "期末市值(万元)", "F010V": "持股变动原因", "F012N": "年薪(万元)",
}

# ── p_stock2219 股东股份冻结 ──

FREEZE_FIELD_MAP = {
    "ORGNAME": "机构名称", "DECLAREDATE": "公告日期",
    "F001V": "被冻结当事人ID", "F002V": "被冻结当事人",
    "F003V": "被冻结股份性质编码", "F004V": "被冻结股份性质",
    "F005N": "冻结数量(股)", "F006N": "占总股份比例(%)",
    "F007V": "冻结申请人", "F008V": "冻结执行人",
    "F009V": "冻结事项", "F010D": "冻结起始日", "F011D": "冻结终止日",
    "F012D": "解冻日期", "F013N": "累计解冻数量(股)", "F014V": "解冻处理说明",
}

# ── p_stock2220 股东股份质押 ──

PLEDGE_FIELD_MAP = {
    "ORGNAME": "机构名称", "DECLAREDATE": "公告日期",
    "F001V": "出质人", "F002V": "出质人ID", "F003V": "质权人",
    "F004V": "质押股份性质编码", "F005V": "质押股份性质",
    "F006N": "质押数量(股)", "F007N": "占总股本比例(%)",
    "F008V": "质押事项", "F009D": "质押起始日", "F010D": "质押终止日",
    "F011D": "质押解除日", "F012N": "质押解除数量(股)", "F013V": "解除质押说明",
    "F014C": "是否质押式回购", "F018N": "累计质押占总股本比例(%)",
}

# ── p_stock2248 公司受处罚 ──

PENALTY_FIELD_MAP = {
    "ORGID": "公司ID", "ORGNAME": "公司名称", "DECLAREDATE": "公告日期",
    "F001V": "处罚类型编码", "F002V": "处罚类型",
    "F003V": "处罚原因", "F004V": "处罚部门",
    "F005V": "处罚对象", "F006V": "处罚内容",
    "F007N": "处罚金额(元)",
}

# ── p_stock2246 公司诉讼 ──

LAWSUIT_FIELD_MAP = {
    "ORGNAME": "机构名称", "DECLAREDATE": "公告日期",
    "F001V": "原告", "F002V": "被告", "F003V": "公司所处地位",
    "F005V": "案由", "F006N": "涉及金额(元)", "F008V": "币种",
    "F009V": "标的", "F010D": "开庭日期",
    "F011V": "诉讼一审机构", "F012V": "诉讼二审机构",
    "F014V": "一审裁决情况", "F015V": "二审裁决情况",
    "F017V": "判决执行情况", "F018V": "对本公司的影响",
    "F020N": "诉讼费用(元)", "F021N": "偿还金额(元)",
    "F023V": "交易市场",
}

# ══════════════════════════════════════════════════════════════
# 核心字段快捷清单
# ══════════════════════════════════════════════════════════════

CORE_FINANCIAL_FIELDS = [
    "F069D", "F089N", "F090N", "F097N", "F100N", "F101N", "F102N",
    "F076N", "F105N", "F118N", "F121N", "F128N", "F129N",
    "F109N", "F111N", "F112N", "F116N", "F115N", "F122N", "F126N", "F127N",
    "F130N", "F091N", "F092N", "F093N",
    "F003N", "F004N", "F006N", "F008N",
    "F014N", "F017N", "F078N", "F079N", "F041N", "F042N", "F043N",
    "F052N", "F053N", "F054N", "F056N",
    "F059N", "F060N", "F063N", "F066N", "F067N", "F082N",
    "F131N", "F132N", "F133N", "F142N", "F143N",
]


# ══════════════════════════════════════════════════════════════
# 客户端
# ══════════════════════════════════════════════════════════════

class CninfoClient:
    """深证信数据服务平台 API 客户端"""

    BASE_URL = "http://webapi.cninfo.com.cn"
    BASE_URL_HTTPS = "https://webapi.cninfo.com.cn"

    def __init__(self):
        self._mcode = None
        self.session = requests.Session()

    @property
    def mcode(self):
        if self._mcode is None:
            self._mcode = _gen_mcode()
        return self._mcode

    def _headers(self, content_type=None):
        h = {
            "Accept-Enckey": self.mcode,
            "Accept": "*/*",
            "Referer": f"{self.BASE_URL_HTTPS}/",
            "Origin": self.BASE_URL_HTTPS,
            "X-Requested-With": "XMLHttpRequest",
        }
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _get(self, path, params=None):
        r = self.session.get(
            f"{self.BASE_URL}{path}", params=params,
            headers=self._headers(), timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("resultcode") in (401, 402, 416):
            raise RuntimeError(f"API error {data.get('resultcode')}: {data.get('resultmsg')}")
        return data

    def _post(self, path, data=None, params=None):
        r = self.session.post(
            f"{self.BASE_URL}{path}", data=data, params=params,
            headers=self._headers("application/x-www-form-urlencoded; charset=UTF-8"),
            timeout=30,
        )
        r.raise_for_status()
        resp = r.json()
        if isinstance(resp, dict) and resp.get("resultcode") in (401, 402, 416):
            raise RuntimeError(f"API error {resp.get('resultcode')}: {resp.get('resultmsg')}")
        return resp

    # ── 1. 公司概况 ──────────────────────────────────────

    def company_profile(self, scode):
        """公司概况 (p_sysapi1133)

        Returns: dict with ORGNAME, F015V(主营业务), F016V(经营范围),
                 F017V(公司简介), F006D(上市日期), F032V(行业) 等
        """
        return self._post("/api/sysapi/p_sysapi1133", params={"scode": scode})

    def company_basic_info(self, objectid=0, rowcount=1000, columns=None):
        """增量获取公司基本信息 (p_stock2100_inc)"""
        params = {"objectid": objectid, "rowcount": rowcount, "format": "json"}
        if columns:
            params["@column"] = ",".join(columns)
        return self._get("/api/load/p_stock2100_inc", params=params)

    # ── 2. 财务指标 (p_stock2303) ──────────────────────────

    def financial_indicators(self, scode, rdate=None, type_code="071001",
                             sdate=None, edate=None, columns=None, limit=None):
        """个股报告期财务指标 — 143字段"""
        body = {"scode": scode, "type": type_code}
        if rdate:
            body["rdate"] = rdate
        if sdate:
            body["sdate"] = sdate
        if edate:
            body["edate"] = edate
        if columns:
            body["@column"] = ",".join(columns)
        if limit:
            body["@limit"] = str(limit)
        return self._post("/api/stock/p_stock2303", data=body)

    def financial_multi_year(self, scode, years=None, sdate=None, edate=None,
                             fields=None, annual_only=True):
        """多年财务数据 → DataFrame（列名自动转中文）

        Args:
            scode: 股票代码
            years: [2024, 2023, 2022] → 自动转 sdate/edate
            annual_only: 仅保留年报 (12-31)
        """
        if fields is None:
            fields = CORE_FINANCIAL_FIELDS

        if years and not sdate:
            ys = sorted(years)
            sdate, edate = f"{ys[0]}-12-31", f"{ys[-1]}-12-31"

        data = self.financial_indicators(
            scode, sdate=sdate, edate=edate,
            columns=fields if not (years and len(years) == 1) else fields,
        )
        if years and len(years) == 1 and not sdate:
            data = self.financial_indicators(
                scode, rdate=f"{years[0]}-12-31", columns=fields,
            )

        records = data.get("records", [])
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, FINANCIAL_FIELD_MAP), inplace=True)
        if "F069D" in df.columns:
            df["报告年度"] = pd.to_datetime(df["F069D"])
        elif "报告年度" in df.columns:
            df["报告年度"] = pd.to_datetime(df["报告年度"])

        if annual_only and "报告年度" in df.columns:
            df = df[df["报告年度"].dt.month == 12]

        return df.sort_values("报告年度", ascending=False).reset_index(drop=True)

    # ── 3. TTM财务指标 (p_stock2334) ──────────────────────

    def ttm_indicators(self, scode, latest_only=True):
        """TTM主要财务指标 → DataFrame

        Args:
            scode: 股票代码
            latest_only: True=仅最新一期, False=全部历史
        """
        state = "2" if latest_only else "1"
        data = self._post("/api/stock/p_stock2334",
                          data={"scode": scode, "state": state})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, TTM_FIELD_MAP), inplace=True)
        if "F001D" in df.columns:
            df["报告年度"] = pd.to_datetime(df["F001D"])
        return df.sort_values("报告年度", ascending=False).reset_index(drop=True)

    # ── 3b. 单季利润表 (p_stock2329) ──────────────────────────

    def quarterly_income(self, scode, latest_only=False, limit=8):
        """单季财务利润表 → DataFrame

        Args:
            scode: 股票代码
            latest_only: True=仅最新一季, False=最近N季
            limit: latest_only=False 时返回的季度数
        """
        data = {"scode": scode, "state": "2" if latest_only else "1"}
        if not latest_only:
            data["@limit"] = str(limit)
            data["@orderby"] = "F001D:desc"
        resp = self._post("/api/stock/p_stock2329", data=data)
        records = resp.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, INCOME_STATEMENT_FIELD_MAP), inplace=True)
        if "F001D" in df.columns:
            df["报告年度"] = pd.to_datetime(df["F001D"])
        return df.sort_values("报告年度", ascending=False).reset_index(drop=True)

    # ── 3c. 单季现金流量表 (p_stock2330) ──────────────────────

    def quarterly_cashflow(self, scode, latest_only=False, limit=8):
        """单季现金流量表 → DataFrame

        Args:
            scode: 股票代码
            latest_only: True=仅最新一季
            limit: latest_only=False 时返回的季度数
        """
        data = {"scode": scode, "state": "2" if latest_only else "1"}
        if not latest_only:
            data["@limit"] = str(limit)
            data["@orderby"] = "F001D:desc"
        resp = self._post("/api/stock/p_stock2330", data=data)
        records = resp.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, CASHFLOW_STATEMENT_FIELD_MAP), inplace=True)
        if "F001D" in df.columns:
            df["报告年度"] = pd.to_datetime(df["F001D"])
        return df.sort_values("报告年度", ascending=False).reset_index(drop=True)

    # ── 3d. TTM利润表 (p_stock2332) ──────────────────────────

    def ttm_income(self, scode, latest_only=True):
        """TTM财务利润表 → DataFrame（字段同单季利润表，但值为滚动12个月合计）

        Args:
            scode: 股票代码
            latest_only: True=仅最新一期
        """
        data = {"scode": scode, "state": "2" if latest_only else "1"}
        if not latest_only:
            data["@limit"] = "8"
            data["@orderby"] = "F001D:desc"
        resp = self._post("/api/stock/p_stock2332", data=data)
        records = resp.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, INCOME_STATEMENT_FIELD_MAP), inplace=True)
        if "F001D" in df.columns:
            df["报告年度"] = pd.to_datetime(df["F001D"])
        return df.sort_values("报告年度", ascending=False).reset_index(drop=True)

    # ── 3e. TTM现金流量表 (p_stock2333) ──────────────────────

    def ttm_cashflow(self, scode, latest_only=True):
        """TTM现金流量表 → DataFrame（字段同单季现金流量表，但值为滚动12个月合计）

        Args:
            scode: 股票代码
            latest_only: True=仅最新一期
        """
        data = {"scode": scode, "state": "2" if latest_only else "1"}
        if not latest_only:
            data["@limit"] = "8"
            data["@orderby"] = "F001D:desc"
        resp = self._post("/api/stock/p_stock2333", data=data)
        records = resp.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, CASHFLOW_STATEMENT_FIELD_MAP), inplace=True)
        if "F001D" in df.columns:
            df["报告年度"] = pd.to_datetime(df["F001D"])
        return df.sort_values("报告年度", ascending=False).reset_index(drop=True)

    # ── 3f. 指数样本股变动 (p_index2914_inc) ──────────────────

    def index_constituent_changes(self, index_code=None, limit=100):
        """指数样本股变动 → DataFrame

        Args:
            index_code: 指数代码，如 '931152'（中证创新药），不传=全量
            limit: 返回条数
        """
        params = {"objectid": 0, "rowcount": limit, "format": "json",
                  "@orderby": "VARYDATE:desc"}
        data = self._get("/api/load/p_index2914_inc", params=params)
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        # 重命名关键列
        rename = {
            "INDEXCODE": "指数代码", "INDEXNAME": "指数名称",
            "DECLAREDATE": "公告日期", "VARYDATE": "变动日期",
            "SECCODE": "证券代码", "SECNAME": "证券简称",
            "F001V": "变动原因编码", "F002V": "变动原因",
            "F003C": "最新记录标识", "MEMO": "备注",
        }
        df.rename(columns=rename, inplace=True)
        if index_code and "指数代码" in df.columns:
            df = df[df["指数代码"] == index_code]
        return df.reset_index(drop=True)

    # ── 4. 投资评级 (p_stock2205) ──────────────────────────

    def investment_ratings(self, scode, limit=20):
        """投资评级+目标价 → DataFrame

        Returns columns: 发布日期, 研究机构, 研究员, 投资评级,
                         评级变化, 目标价下限, 目标价上限
        """
        data = self._post("/api/sysapi/p_stock2205",
                          data={"scode": scode, "@limit": str(limit),
                                "@orderby": "DECLAREDATE:desc"})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, RATING_FIELD_MAP), inplace=True)
        return df

    # ── 5. 个股研报摘要 (p_info3097_inc) ────────────────────

    def research_reports(self, scode=None, limit=20):
        """个股研报摘要 → DataFrame

        Args:
            scode: 股票代码（可选，不传=全量最新）
            limit: 返回条数

        Note: 这是 load 类增量接口，scode 过滤在服务端可能不生效，
              如需按股票筛选建议传较大 limit 后本地过滤。
        """
        params = {"objectid": 0, "rowcount": limit, "format": "json",
                  "@orderby": "F001D:desc"}
        data = self._get("/api/load/p_info3097_inc", params=params)
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, RESEARCH_REPORT_FIELD_MAP), inplace=True)

        # 本地过滤
        if scode and "SECCODE" in df.columns:
            df = df[df["SECCODE"] == scode]
        return df.reset_index(drop=True)

    # ── 6. 行业PE (p_sysapi1087) ──────────────────────────

    def industry_pe(self, date=None):
        """全行业PE数据 → DataFrame

        Returns: 120个行业的加权PE/等权PE/中位数PE/公司数/总市值
        """
        data = self._post("/api/sysapi/p_sysapi1087", data={})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, INDUSTRY_PE_FIELD_MAP), inplace=True)
        return df

    # ── 7. 分红数据 (p_sysapi1139) ──────────────────────────

    def dividends(self, scode):
        """个股历史分红 → DataFrame

        Returns: 分红年度, 分红方案, 每股分红, 股权登记日, 除权除息日, 分红类型
        """
        data = self._post("/api/sysapi/p_sysapi1139", params={"scode": scode})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, DIVIDEND_FIELD_MAP), inplace=True)
        return df

    # ── 8. 股东户数 (p_sysapi1029) ──────────────────────────

    def shareholder_structure(self, scode):
        """股东户数变化趋势 → DataFrame

        Returns: 截止日期, 股东户数, 户均持股, 户均持股市值
        """
        data = self._post("/api/sysapi/p_sysapi1029", params={"scode": scode})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        # 过滤只保留该股票
        if "SECCODE" in df.columns:
            df = df[df["SECCODE"] == scode]
        df.rename(columns=_build_rename(df.columns, SHAREHOLDER_FIELD_MAP), inplace=True)
        return df

    # ── 9. 股本变动 (p_stock2215) ──────────────────────────

    def share_changes(self, scode):
        """股本变动历史 → DataFrame

        Returns: 变动日期, 变动原因, 总股本, 流通A股, 限售A股
        """
        data = self._post("/api/stock/p_stock2215", data={"scode": scode})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, SHARE_CHANGE_FIELD_MAP), inplace=True)
        return df

    # ── 10. 行业分类 (p_stock2110) ─────────────────────────

    def industry_classification(self, scode):
        """个股的所有行业分类标准 → DataFrame

        Returns: 证监会/申万/新财富等8套标准下的行业归属
        """
        data = self._post("/api/stock/p_stock2110", data={"scode": scode})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, INDUSTRY_CLASS_FIELD_MAP), inplace=True)
        return df

    # ── 11. IPO概况 (p_sysapi1134) ─────────────────────────

    def ipo_summary(self, scode):
        """IPO发行概况 → DataFrame

        Returns: 发行价, 发行市盈率, 发行股数, 募集资金, 主承销商, 上市日期
        """
        data = self._post("/api/sysapi/p_sysapi1134", params={"scode": scode})
        records = data.get("records", [])
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, IPO_FIELD_MAP), inplace=True)
        return df

    # ── 15. 业绩预告 (p_stock2238) ─────────────────────────

    def performance_forecast(self, scode=None, ftype=None, sdate=None, edate=None, limit=20):
        """业绩预告 → DataFrame
        Args: scode=股票代码, ftype='035003'(预增)/'035006'(预亏),
              sdate/edate=YYYYMMDD格式
        Note: 大盘蓝筹通常不发业绩预告（波动<50%），小盘/波动大公司更常见
        """
        data = {"@limit": str(limit), "@orderby": "DECLAREDATE:desc"}
        if scode: data["scode"] = scode
        if ftype: data["type"] = ftype
        if sdate: data["sdate"] = sdate
        if edate: data["edate"] = edate
        resp = self._post("/api/stock/p_stock2238", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, FORECAST_FIELD_MAP), inplace=True)
        return df

    # ── 16. 业绩快报 (p_stock2328) ─────────────────────────

    def performance_express(self, scode, sdate=None, edate=None, limit=10):
        """业绩快报 → DataFrame"""
        data = {"scode": scode, "@limit": str(limit), "@orderby": "DECLAREDATE:desc"}
        if sdate: data["sdate"] = sdate
        if edate: data["edate"] = edate
        resp = self._post("/api/stock/p_stock2328", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, EXPRESS_FIELD_MAP), inplace=True)
        return df

    # ── 17. 十大流通股东 (p_stock2209) ─────────────────────

    def top10_holders(self, scode, rdate=None):
        """十大流通股东 → DataFrame（默认最新报告期）"""
        data = {"scode": scode, "@limit": "12", "@orderby": "F001N:asc"}
        if rdate: data["rdate"] = rdate
        resp = self._post("/api/stock/p_stock2209", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, TOP10_HOLDER_FIELD_MAP), inplace=True)
        # Keep only latest period if multiple returned
        if not rdate and "截止日期" in df.columns:
            latest = df["截止日期"].max()
            df = df[df["截止日期"] == latest]
        return df

    # ── 18. 高管持股变动 (p_stock2218) ─────────────────────

    def executive_trades(self, scode, sdate=None, edate=None, limit=20):
        """高管持股变动 → DataFrame"""
        data = {"scode": scode, "@limit": str(limit), "@orderby": "DECLAREDATE:desc"}
        if sdate: data["sdate"] = sdate
        if edate: data["edate"] = edate
        resp = self._post("/api/stock/p_stock2218", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, EXEC_TRADE_FIELD_MAP), inplace=True)
        return df

    # ── 19. 股东股份冻结 (p_stock2219) ─────────────────────

    def share_freeze(self, scode, latest_only=True):
        """股东股份冻结 → DataFrame"""
        data = {"scode": scode, "state": "2" if latest_only else "1"}
        resp = self._post("/api/stock/p_stock2219", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, FREEZE_FIELD_MAP), inplace=True)
        return df

    # ── 20. 股东股份质押 (p_stock2220) ─────────────────────

    def share_pledge(self, scode, latest_only=True):
        """股东股份质押 → DataFrame"""
        data = {"scode": scode, "state": "2" if latest_only else "1"}
        resp = self._post("/api/stock/p_stock2220", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, PLEDGE_FIELD_MAP), inplace=True)
        return df

    # ── 21. 公司受处罚 (p_stock2248) ───────────────────────

    def company_penalties(self, scode, sdate=None, edate=None, limit=20):
        """公司受处罚 → DataFrame"""
        data = {"scode": scode, "@limit": str(limit), "@orderby": "DECLAREDATE:desc"}
        if sdate: data["sdate"] = sdate
        if edate: data["edate"] = edate
        resp = self._post("/api/stock/p_stock2248", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, PENALTY_FIELD_MAP), inplace=True)
        return df

    # ── 22. 公司诉讼 (p_stock2246) ─────────────────────────

    def company_lawsuits(self, scode, sdate=None, edate=None, limit=20):
        """公司诉讼 → DataFrame"""
        data = {"scode": scode, "@limit": str(limit), "@orderby": "DECLAREDATE:desc"}
        if sdate: data["sdate"] = sdate
        if edate: data["edate"] = edate
        resp = self._post("/api/stock/p_stock2246", data=data)
        records = resp.get("records", [])
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        df.rename(columns=_build_rename(df.columns, LAWSUIT_FIELD_MAP), inplace=True)
        return df

    # ── 23. 公告查询与PDF下载 ────────────────────────────

    _stock_org_ids = None

    @classmethod
    def _load_org_ids(cls):
        if cls._stock_org_ids is None:
            import requests as _r
            resp = _r.get("http://www.cninfo.com.cn/new/data/szse_stock.json", timeout=30)
            cls._stock_org_ids = {item["code"]: item["orgId"] for item in resp.json()["stockList"]}
        return cls._stock_org_ids

    def list_announcements(self, scode, category="category_ndbg_szsh",
                           start_date="2020-01-01", end_date="2026-12-31",
                           max_pages=3, page_size=30):
        """查询公告列表 → DataFrame（含PDF下载链接）
        Args:
            scode: 股票代码
            category: 公告类别
                'category_ndbg_szsh'=年报, 'category_bndbg_szsh'=半年报,
                'category_yjdbg_szsh'=一季报, 'category_sjdbg_szsh'=三季报,
                'category_yjygjxz_szsh'=业绩预告, 'category_sf_szsh'=首发(招股书)
            start_date/end_date: 日期范围 YYYY-MM-DD
            max_pages: 最大翻页数
        Returns: DataFrame with columns: 发布日期, 标题, PDF_URL, 文件大小KB
        """
        org_ids = self._load_org_ids()
        org_id = org_ids.get(scode)
        if not org_id:
            raise ValueError(f"未找到股票代码 {scode} 的 orgId")

        all_anns = []
        for page in range(1, max_pages + 1):
            r = requests.post(
                "http://www.cninfo.com.cn/new/hisAnnouncement/query",
                data={
                    "pageNum": str(page), "pageSize": str(page_size),
                    "column": "szse", "tabName": "fulltext",
                    "plate": "", "stock": f"{scode},{org_id}",
                    "searchkey": "", "secid": "", "category": category,
                    "trade": "",
                    "seDate": f"{start_date}~{end_date}",
                    "sortName": "", "sortType": "", "isHLtitle": "true",
                },
                headers={"Accept": "application/json", "Referer": "http://www.cninfo.com.cn/"},
                timeout=30,
            )
            data = r.json()
            anns = data.get("announcements") or []
            if not anns:
                break
            all_anns.extend(anns)

        if not all_anns:
            return pd.DataFrame()

        rows = []
        for a in all_anns:
            ts = a.get("announcementTime", 0) / 1000
            dt = pd.Timestamp(ts, unit="s")
            rows.append({
                "发布日期": dt,
                "标题": a.get("announcementTitle", ""),
                "PDF_URL": f"https://static.cninfo.com.cn/{a.get('adjunctUrl', '')}",
                "文件大小KB": a.get("adjunctSize", 0),
            })
        df = pd.DataFrame(rows)
        return df.sort_values("发布日期", ascending=False).reset_index(drop=True)

    def download_report(self, url, save_path):
        """下载公告PDF到本地"""
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        r.raise_for_status()
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_bytes(r.content)
        return Path(save_path)

    def download_latest_annual_report(self, scode, output_dir=None):
        """下载最新年报PDF → 返回文件路径"""
        df = self.list_announcements(scode, category="category_ndbg_szsh",
                                     max_pages=1, page_size=5)
        if df.empty:
            raise ValueError(f"未找到 {scode} 的年报")
        # 排除摘要/英文版，取主年报
        main = df[~df["标题"].str.contains("摘要|英文", na=False)]
        if main.empty:
            main = df
        row = main.iloc[0]
        if output_dir is None:
            output_dir = Path.cwd() / "财报" / "_Inbox"
        fname = f"{scode}_{row['标题'].replace('/','_')}.pdf"
        save_path = Path(output_dir) / fname
        return self.download_report(row["PDF_URL"], save_path)

    # ── 23. 互动易 Q&A (irm.cninfo.com.cn) ──────────────────

    def irm_qa(self, scode, pages=3, answered_only=True):
        """互动易投资者问答 -> DataFrame（无需 mcode,公共API）"""
        r = requests.post(
            "https://irm.cninfo.com.cn/newircs/index/queryKeyboardInfo",
            params={"_t": "1691144074"}, data={"keyWord": scode},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
        )
        org_id = r.json()["data"][0]["secid"]

        rows = []
        for page in range(1, pages + 1):
            r = requests.post(
                "https://irm.cninfo.com.cn/newircs/company/question",
                params={
                    "_t": "1691142650", "stockcode": scode,
                    "orgId": org_id, "pageSize": "50", "pageNum": str(page),
                    "keyWord": "", "startDay": "", "endDay": "",
                },
                headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
            )
            for item in r.json().get("rows", []):
                answer = (item.get("attachedContent") or "").strip()
                if answered_only and not answer:
                    continue
                rows.append({
                    "提问时间": pd.Timestamp(item.get("pubDate", 0), unit="ms"),
                    "提问者": item.get("authorName", ""),
                    "问题": item.get("mainContent", ""),
                    "回答内容": answer,
                    "回答者": item.get("attachedAuthor", ""),
                })
        return pd.DataFrame(rows)

    # ── 批量快捷方法 ──────────────────────────────────────

    def deep_analysis_bundle(self, scode, years=None):
        """深度分析数据包 — 一次性拉取核心数据

        Returns: dict with keys:
            profile, financials, ttm, ratings, dividends, shareholders, ipo
        """
        if years is None:
            years = [2020, 2021, 2022, 2023, 2024]

        return {
            "profile": self.company_profile(scode),
            "financials": self.financial_multi_year(scode, years=years),
            "ttm": self.ttm_indicators(scode),
            "quarterly_income": self.quarterly_income(scode, limit=8),
            "quarterly_cashflow": self.quarterly_cashflow(scode, limit=8),
            "ratings": self.investment_ratings(scode, limit=10),
            "dividends": self.dividends(scode),
            "shareholders": self.shareholder_structure(scode),
            "top10_holders": self.top10_holders(scode),
            "executive_trades": self.executive_trades(scode, limit=20),
            "pledge": self.share_pledge(scode),
            "freeze": self.share_freeze(scode),
            "penalties": self.company_penalties(scode),
            "lawsuits": self.company_lawsuits(scode),
            "forecast": self.performance_forecast(scode, limit=5),
            "ipo": self.ipo_summary(scode),
        }


# ══════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════

def _build_rename(columns, field_map):
    """将 F-code / 原始列名映射为中文名"""
    rename = {}
    for col in columns:
        if col in field_map:
            rename[col] = field_map[col]
    # 通用映射
    for col in columns:
        if col not in rename:
            if col in ("ORGNAME",):  rename[col] = "机构名称"
            elif col in ("SECCODE",): rename[col] = "证券代码"
            elif col in ("SECNAME",): rename[col] = "证券简称"
            elif col in ("STARTDATE",): rename[col] = "开始日期"
            elif col in ("ENDDATE",): rename[col] = "截止日期"
    return rename
