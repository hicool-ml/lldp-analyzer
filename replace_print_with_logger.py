"""
批量替换print为logger的脚本
智能判断应该使用哪个日志级别
"""

import re

# 读取parser.py
with open('lldp/parser.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义替换规则
replacements = [
    # DEBUG级别的print
    (r'print\(f"\[DEBUG\] (.*?)"\)', r'logger.debug("\1")'),
    (r"print\(f'\[DEBUG\] (.*?)'\)", r'logger.debug("\1")'),
    (r'print\(f"\[DEBUG\] (.*?)\\\\n"\)', r'logger.debug("\1")'),

    # ERROR级别的print
    (r'print\(f"\[ERROR\] (.*?)"\)', r'logger.error("\1")'),
    (r"print\(f'\[ERROR\] (.*?)'\)", r'logger.error("\1")'),

    # WARNING级别的print
    (r'print\(f"\[WARNING\] (.*?)"\)', r'logger.warning("\1")'),
    (r"print\(f'\[WARNING\] (.*?)'\)", r'logger.warning("\1")'),
]

# 应用替换
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# 处理hex输出限制
content = re.sub(r'(\.hex\(\))(\[?(:?\d+)?\]?)', r'[:MAX_HEX_DISPLAY]\1', content)

# 写回文件
with open('lldp/parser.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Print→Logger替换完成！")
