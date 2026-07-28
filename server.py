"""
华小招 - API服务器
本地运行，作为DeepSeek API的代理，避免前端暴露API Key
"""
import http.server
import json
import urllib.request
import urllib.error
import os
import re
import traceback
import sys

# DeepSeek API 配置
API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/anthropic/messages")
API_KEY = os.environ["DEEPSEEK_API_KEY"]
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")

SYSTEM_PROMPT = """你是"华小招"，华泰证券校园招聘AI智能助手。你的职责是回答关于华泰证券2026校园招聘的问题。

## 你的身份
- 名称：华小招
- 定位：华泰证券校招AI助手，7×24小时在线
- 风格：专业、简洁、友好，像一位耐心的HR同事

## 知识范围（必须严格基于以下信息回答）

### 公司概况
华泰证券是一家领先的科技驱动型综合证券集团，1991年成立，在上海（A股）、香港（H股）、伦敦（GDR）三地上市。业务覆盖财富管理、机构服务、投资管理和国际业务四大板块。2025年确立"ALL IN AI"战略，推出AI原生交易终端"AI涨乐"，打造AI平台"泰为"。

### 三大招聘项目
1. 秋季校园招聘：面向2026届毕业生（大陆2026.1-7月毕业；港澳台及海外2025.7-2026.6毕业），专业不限，工作地点覆盖北京、上海、深圳、南京、香港、新加坡及全国各分公司。流程：网申→在线测评→专业面试→实习考察(12月-次年1月)→录用通知(次年2月)。

2. Fintech金融科技专场：面向2026及2027届，信息技术/理工类优先，免实习考察。工作地点北京、上海、深圳、南京。流程：网申→在线笔试→专业面试→录用通知。滚动招聘，招满即止。

3. GTP跨境管培：面向大陆2027届及港澳台海外2025.7-2027.6毕业。香港工作，跨境轮岗。流程：网申→面试评估→录用通知。滚动招聘。

### 投递规则
- 每位同学最多申请3个岗位
- 三个项目可同时投递，互不影响
- 投递官网：job.htsc.com.cn

### 联系方式
- 招聘官网：job.htsc.com.cn
- 招聘邮箱：zhaopin.ht@htsc.com

## 回答规则
1. 只回答与华泰证券校招相关的问题
2. 不确定的信息不要编造，引导用户查看官网
3. 回答简洁，控制在200字以内
4. 如果用户问的是寒暄（你好、你是谁等），友好回应并介绍自己
5. 用户问"我的投递状态"时，告知他们可以在个人主页绑定手机号后查询"""

class ChatHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            if self.path == '/api/chat':
                content_length = int(self.headers.get('Content-Length', 0))
                raw = self.rfile.read(content_length)
                body = json.loads(raw.decode('utf-8', errors='replace'))
                user_msg = body.get('message', '')

                if not user_msg.strip():
                    self._json_response({'reply': '请告诉我你想问什么吧~'})
                    return

                try:
                    reply = self._call_deepseek(user_msg)
                    self._json_response({'reply': reply})
                except Exception as e:
                    traceback.print_exc()
                    self._json_response({'reply': '抱歉，AI服务暂时不可用，请稍后再试~', 'fallback': True})

            elif self.path == '/':
                self._serve_file('index.html', 'text/html; charset=utf-8')
            else:
                self.send_error(404)
        except Exception as e:
            traceback.print_exc()
            self.send_error(500)

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._serve_file('index.html', 'text/html; charset=utf-8')
        elif self.path == '/api/health':
            self._json_response({'status': 'ok'})
        else:
            super().do_GET()

    def _serve_file(self, filename, content_type):
        try:
            with open(filename, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def _json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _call_deepseek(self, user_msg):
        payload = json.dumps({
            "model": MODEL,
            "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ]
        }).encode('utf-8')

        req = urllib.request.Request(API_URL, data=payload, headers={
            'Content-Type': 'application/json',
            'x-api-key': API_KEY,
            'anthropic-version': '2023-06-01'
        })

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            # DeepSeek Anthropic兼容接口 - content是数组，包含thinking和text块
            content_blocks = result.get('content', [])
            text_parts = []
            for block in content_blocks:
                if block.get('type') == 'text':
                    text_parts.append(block.get('text', ''))
            if text_parts:
                return ''.join(text_parts)
            # fallback: 尝试choices格式
            if 'choices' in result:
                return result['choices'][0]['message']['content']
            return '收到你的问题了，但我暂时无法处理~'

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = 8080
    server = http.server.HTTPServer(('0.0.0.0', port), ChatHandler)
    print(f'华小招 API服务器已启动: http://localhost:{port}')
    print(f'API端点: http://localhost:{port}/api/chat')
    server.serve_forever()

if __name__ == '__main__':
    main()
