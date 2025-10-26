import os

def custom_encode(text, key='conf_secret_key'):
    """
    自定义编码函数（不使用base64）
    1. 使用密钥对每个字符的ASCII值进行位移和映射
    2. 使用特殊字符分隔编码后的字符
    """
    # 如果text为空，返回空字符串
    if not text:
        return ''
    
    encoded_chars = []
    key_length = len(key)
    
    for i, char in enumerate(text):
        # 获取字符的ASCII值
        char_code = ord(char)
        # 获取密钥对应位置的ASCII值
        key_code = ord(key[i % key_length])
        
        # 位移操作：左移3位，然后与密钥进行异或
        shifted = (char_code << 3) ^ key_code
        # 转换为字符串格式，使用3位数字表示（确保固定长度）
        encoded_str = f"{shifted:03d}"
        encoded_chars.append(encoded_str)
    
    # 使用特殊字符'_'连接编码后的部分
    return '_'.join(encoded_chars)

def custom_decode(encoded_text, key='conf_secret_key'):
    """
    自定义解码函数（不使用base64）
    1. 分割编码字符串
    2. 对每个部分进行逆运算得到原始字符
    """
    # 如果encoded_text为空，返回空字符串
    if not encoded_text:
        return ''
    
    try:
        # 分割编码字符串
        encoded_parts = encoded_text.split('_')
        key_length = len(key)
        decoded_chars = []
        
        for i, part in enumerate(encoded_parts):
            # 转换回整数
            shifted = int(part)
            # 获取密钥对应位置的ASCII值
            key_code = ord(key[i % key_length])
            
            # 逆运算：先异或，再右移3位
            char_code = (shifted ^ key_code) >> 3
            # 转换回字符
            decoded_chars.append(chr(char_code))
        
        return ''.join(decoded_chars)
    except Exception as e:
        print(f"解码错误: {e}")
        return ''

# 获取配置URL
conf_url = os.environ.get('CONF_URL', 'https://example.com/conf/2024')
print(f"原始URL: {conf_url}")

# 编码
encoded_string = custom_encode(conf_url)
print(f"编码后: {encoded_string}")

# 解码
decoded_string = custom_decode(encoded_string)
print(f"解码后: {decoded_string}")

# 验证编码解码是否正确
if conf_url == decoded_string:
    print("✓ 编码解码验证成功!")
else:
    print("✗ 编码解码验证失败!")