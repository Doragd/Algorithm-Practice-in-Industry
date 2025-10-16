import requests

# 飞书机器人 Webhook URL
webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/75df3d53-9355-4b34-8e05-586f852e9288"

# 要发送的消息
message = {
    "msg_type": "text",
    "content": {
        "text": "我是恁爹！"
    }
}

# 发送消息到飞书
response = requests.post(webhook_url, json=message)

if response.status_code == 200:
    print("消息推送成功")
else:
    print(f"消息推送失败，状态码: {response.status_code}")
