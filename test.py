import base64
import os

conf_url = os.environ.get('CONF_URL', '')

original_string = conf_url
original_bytes = original_string.encode('utf-8')
encoded_bytes = base64.b64encode(original_bytes)
encoded_string = encoded_bytes.decode('utf-8')

print(f"Base64 编码后: {encoded_string}")