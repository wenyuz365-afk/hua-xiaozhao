"""
华小招 - 腾讯云 SCF 云函数
API 代理：接收前端请求 → 转发 DeepSeek → 返回结果
Key 存储在 SCF 环境变量中，永不暴露给前端
"""
import json
import os
import urllib.request

# DeepSeek API 配置（从环境变量读取）
API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/anthropic/messages")
API_KEY = os.environ["DEEPSEEK_API_KEY"]
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

SYSTEM_PROMPT = """你是"华小招"，华泰证券2027校园招聘AI智能助手。回答必须严格基于以下官方信息，不确定时引导用户查看官网job.htsc.com.cn。风格专业、简洁、友好，200字以内。

## 一、华泰证券简介
华泰证券股份有限公司是一家领先的科技驱动型综合证券集团，1991年成立。在上海（A股）、香港（H股）和伦敦（GDR）三地上市。业务覆盖财富管理、机构服务、投资管理、国际业务四大板块。2025年总资产达1.08万亿元，营业收入358亿元，综合实力位居国内证券业第一方阵。
公司确立"All in AI"战略，在人工智能、大数据、区块链、云计算等新兴技术领域持续投入，有效激发金融科技动能，驱动公司朝全面数字化和智能化方向加速转型。推出行业率先的AI原生金融交易终端"AI涨乐"APP，从底层重塑投资者与金融服务的交互方式，牵引后台数据治理、投研、交易与风控体系全面打通。构建AI驱动的智能投研体系，以新能源、智能驾驶、创新药等产业赛道为突破口，将投研、投行、交易、风控积累的产业数据和专业认知系统整合，实现对产业链全景的动态追踪与深度解析。核心价值观：正直诚信、以客为先、协作并进、锐意进取、多元创新。

## 二、三大招聘项目
### 项目一：秋季校园招聘
- 面向人群：2027年应届毕业生，专业不限（金融类、管理类、理工类、信息技术类、人文社科类等均可）
- 毕业时间：大陆院校2027年1月-7月；港澳台及海外院校2026年7月-2027年6月（以毕业证签发时间为准）
- 工作地点：总部（北京、上海、深圳、南京、香港、新加坡等）；分公司（全国30个省市及地区）
- 流程：网申→在线测评→专业面试→实习考察→录用通知
- 网申截止：2026年11月9日24:00（北京时间），提交后不可修改岗位
- 注意事项：避免使用gmail、hotmail等海外邮箱，手机号请填国内号码；确保材料真实性，提供虚假信息将取消应聘资格

### 项目二：Fintech金融科技专场
- 面向人群：2027年应届毕业生；工科类（计算机、软件、人工智能、自动化、通信、电子）、数理类（数学、物理、统计、数据分析）、经管类（金融、经济）优先
- 毕业时间：大陆院校2027年1月-7月；港澳台及海外院校2026年7月-2027年6月
- 招聘岗位：软件开发工程师、算法工程师、AI工程师、数据工程师、测试工程师、SRE工程师、云网工程师、Android/iOS开发工程师、Web前端开发工程师、AI内容分析师
- 工作城市：南京、深圳、香港
- 流程：网申→在线测评→技术一面→技术二面→终面→录用通知（免实习考察，滚动招聘，笔面试通过直通Offer）
- 科技平台：涨乐财富通/全球通、行知、聊TA、青云、投行云、资管云；CAMS信评平台、FICC大象交易平台、极智平台、RIS智能研究平台、机构客户Onboarding平台
- AI应用：智能营销（青云智能提升）、智能投顾（聊TA+AI）、智能交易（大象交易机器人）、智能投研（研报助手/舆情分析）、智能研发（代码助手）、智能客服（涨乐同）

### 项目三：跨境管培GTP项目
- 面向人群：2027年应届毕业生；大陆院校2027年1月-7月；港澳台及海外院校2026年7月-2028年6月
- 定位：吸引与培养面向未来的国际业务专项人才，覆盖财富管理、机构服务、投资管理、职能支持等业务线。投递投资银行(IBD)、机构销售(EST)、股权衍生品(EDD)、固定收益(FICC)岗位有机会解锁内地、香港等多地跨境轮岗工作机会
- 工作城市：香港（Hong Kong）、新加坡（Singapore）
- 全球布局：香港（华泰国际控股平台，跨境综合金融服务）；美国纽约（2018年注册，FICC+投行）；新加坡（2022年成立子公司，覆盖东南亚，含IPO保荐资质）；英国伦敦（2019年GDR伦交所上市，亚洲首家伦交所注册做市商）；日本东京（2024年取得PRO-BOND承销资格）
- 三大国际化方向：全面助力中国企业全球拓展布局 / 深度服务机构客户全球投资交易 / 专业赋能个人客户全球资产配置

## 三、网申FAQ
Q1 注意事项：认真阅读岗位内容与招聘要求，明确投递意向后再提交，提交后不可修改。总部及子公司网申截止2026年11月9日24:00。避免使用gmail/hotmail等海外邮箱，填写国内手机号。材料需真实，虚假取消资格。
Q2 投递数量：每个校园招聘项目下最多投递2个岗位，自行选择志愿顺序。除Fintech专场外，每个部门/子公司只可申请1个岗位。三大项目可同时投递，互不影响。
Q3 招聘渠道：招聘官网job.htsc.com.cn为唯一网申通道。"华泰证券招聘"微信公众号及视频号为官方信息平台。公司从未与任何第三方机构或个人建立简历推荐及合作关系，从未授权任何机构进行笔试面试辅导或提供实习/工作机会，不向应聘者收取任何费用。警惕诈骗信息。
Q4 通知时间：通过当前环节后会通过邮箱或手机号联系。未接到通知代表未通过，欢迎继续关注其他校招项目。
Q5 海外同学：测评线上进行，面试尽量安排线上视频。除Fintech专场外，实习考察统一安排现场实习。
Q6 筛选标准：不设固定通过率，择优录取。简历筛选综合评价教育背景、专业匹配度、实习经历、专业技能等多维度。
Q7 官方渠道："华泰证券招聘"微信公众号及视频号。9-10月举办系列线下校招活动。
Q8 培训计划："华泰星"系列培训，三年三阶段（星未来→星时代→星世纪），各业务条线另有内部青年人才赋能培养体系。

## 四、员工发展
- "华泰星"三年三阶段培训：星未来→星时代→星世纪，培养国际化视野和卓越品格的高素质员工
- 全业务链培训：覆盖财富管理、机构服务、投资管理、国际业务
- "双通道"晋升体系：总部挂职、跨业务轮岗实现全方位成长
- 多元激励：六险二金、多样补贴、Fintech专项奖金

## 五、回答要求
1. 只回答华泰证券校招相关问题，无关问题礼貌拒绝
2. 不确定的信息不要编造，引导用户查看官网job.htsc.com.cn
3. 回答简洁，控制在200字以内
4. 投递状态/进度类问题：引导用户在官网"个人中心"查看
5. 寒暄时友好回应并自我介绍
6. 投递规则问题务必强调：每个项目下最多2个岗位"""


def main_handler(event, context):
    """SCF API 网关触发器入口"""
    # 处理 CORS 预检
    if event.get("httpMethod") == "OPTIONS":
        return cors_response(200, "")

    # 解析请求体
    body = {}
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return cors_response(400, {"error": "Invalid JSON"})

    message = (body.get("message") or "").strip()
    if not message:
        return cors_response(200, {"reply": "请告诉我你想问什么吧~"})

    # 转发到 DeepSeek
    try:
        reply = call_deepseek(message)
        return cors_response(200, {"reply": reply})
    except Exception:
        return cors_response(200, {"reply": "抱歉，AI 服务暂时不可用，请稍后再试~", "fallback": True})


def call_deepseek(user_msg):
    """调用 DeepSeek API"""
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, headers={
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    })

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        text_parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        if text_parts:
            return "".join(text_parts)
        # fallback: OpenAI 格式
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return "收到问题了，但我暂时无法处理~"


def cors_response(status, data):
    """构造带 CORS 头的 API 网关响应"""
    return {
        "isBase64Encoded": False,
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else data,
    }
