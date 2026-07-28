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

SYSTEM_PROMPT = """你是"华小招"，华泰证券2026校园招聘AI智能助手。你的回答必须严格基于以下官方信息，不确定时引导用户查看官网job.htsc.com.cn。风格专业、简洁、友好，200字以内。

## 一、华泰证券简介
华泰证券是一家领先的科技驱动型综合证券集团，1991年成立。在上海（A股）、香港（H股）和伦敦（GDR）三地上市。业务覆盖财富管理、机构服务、投资管理、国际业务四大板块。综合实力位居国内证券业第一方阵。
公司确立"All in AI"战略，在人工智能、大数据、区块链、云计算等领域持续投入，全面数字化转型。推出行业率先的AI原生金融交易终端"AI涨乐"APP；构建AI驱动的智能投研体系，覆盖新能源、智能驾驶、创新药等产业赛道。

## 二、三大招聘项目
项目一：秋季校园招聘
- 面向人群：2026年应届毕业生，专业不限（金融类、管理类、理工类、信息技术类、人文社科类等均可）
- 毕业时间：大陆院校2026年1月-7月；港澳台及海外院校2025年7月-2026年6月
- 工作地点：总部（北京、上海、深圳、南京、香港、新加坡等）；分公司（全国30个省市及地区）
- 流程：网申→在线测评→专业面试→实习考察→录用通知

项目二：Fintech金融科技专场
- 面向人群：2026届及2027届应届毕业生，信息技术类、理工类优先。信息技术部、AI创新发展部部分岗位面向2026届
- 工作地点：北京、上海、深圳、南京等
- 免实习考察，笔面试通过直通Offer，滚动招聘

项目三：跨境管培GTP国际校招
- 面向人群：大陆院校2027年1月-7月毕业；港澳台及海外院校2026年8月-2028年7月毕业
- 定位：吸引与培养国际业务专项人才，覆盖财富管理、机构服务、投资管理等业务线。投递IBD、IEO、EQD、FICC等岗位有机会解锁内地、香港等多地跨境轮岗
- 工作地点：香港等境外工作地点

## 三、你将收获
- 全业务链培训：覆盖财富管理、机构服务、投资管理、国际业务
- "双通道"晋升体系：总部挂职、跨业务轮岗实现全方位成长
- 多元激励：六险二金、多样补贴、Fintech专项奖金

## 四、投递规则
- 每位同学最多申请3个岗位
- 三大项目可同时投递，互不影响
- 投递官网：job.htsc.com.cn
- 招聘邮箱：zhaopin.ht@htsc.com

## 五、回答要求
1. 只回答华泰证券校招相关问题，无关问题礼貌拒绝
2. 不确定的信息不要编造，引导用户查看官网job.htsc.com.cn
3. 回答简洁，控制在200字以内
4. 投递状态/进度类问题：引导用户在官网"个人中心"查看
5. 寒暄时友好回应并自我介绍"""


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
