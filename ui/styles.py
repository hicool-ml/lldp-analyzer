"""
LLDP Analyzer - UI Styles (QSS)
🔥 优化A: 提取所有QSS样式到独立文件，避免CSS Bloat

这个文件集中管理所有UI样式，便于维护和修改
"""

# ==================== 全局样式 ====================

GLOBAL_STYLES = """
/* 主窗口样式 */
QMainWindow {
    background-color: #0f172a;
    font-family: 'Segoe UI Variable', 'Microsoft YaHei UI';
}

/* 滚动条样式 */
QScrollBar:vertical {
    border: none;
    background: #1e293b;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #475569;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #64748b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""

# ==================== 按钮样式 ====================

BUTTON_STYLE_TEMPLATE = """
QPushButton {{
    background-color: {color};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {hover_color};
    transform: translateY(-1px);
}}

QPushButton:pressed {{
    background-color: {pressed_color};
    transform: translateY(1px);
}}

QPushButton:disabled {{
    background-color: #475569;
    color: #94a3b8;
}}
"""

def get_button_style(color: str, hover_color: str = None, pressed_color: str = None) -> str:
    """
    生成按钮样式

    Args:
        color: 主颜色
        hover_color: 悬停颜色（可选，默认自动计算）
        pressed_color: 按下颜色（可选，默认自动计算）
    """
    if hover_color is None:
        hover_color = color  # 简化版
    if pressed_color is None:
        pressed_color = color  # 简化版

    return BUTTON_STYLE_TEMPLATE.format(
        color=color,
        hover_color=hover_color,
        pressed_color=pressed_color
    )

# 预定义按钮样式
BUTTON_PRIMARY = get_button_style("#2563eb", "#3b82f6", "#1d4ed8")    # 蓝色
BUTTON_DANGER = get_button_style("#dc2626", "#ef4444", "#b91c1c")    # 红色
BUTTON_SUCCESS = get_button_style("#059669", "#10b981", "#047857")   # 绿色

# ==================== 卡片样式 ====================

CARD_STYLE = """
QFrame {
    background-color: #1e293b;
    border-radius: 8px;
    border: 1px solid #334155;
}
"""

CARD_HEADER_STYLE = """
QLabel {
    color: #f1f5f9;
    font-size: 15px;
    font-weight: 700;
}
"""

CARD_SUBTITLE_STYLE = """
QLabel {
    color: #94a3b8;
    font-size: 13px;
}
"""

# ==================== 设备卡片样式 ====================

DEVICE_CARD_LABEL_NAME = "color:#94a3b8; font-size:13px;"
DEVICE_CARD_LABEL_VALUE = "color:#22c55e; font-weight:600; font-size:13px;"

DEVICE_CARD_STYLE = """
/* 设备名称 */
.device_name {
    color: #fbbf24;
    font-weight: 600;
}

/* 设备型号 */
.device_model {
    color: #64748b;
}

/* 端口角色 */
.port_role {
    color: #94a3b8;
    font-style: italic;
}

/* 协议 */
.protocol {
    color: #94a3b8;
    font-style: italic;
}

/* 端口ID */
.port_id {
    color: #94a3b8;
    font-style: italic;
}
"""

# ==================== 下拉框样式 ====================

COMBO_BOX_STYLE = """
QComboBox {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #64748b;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #94a3b8;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #475569;
    selection-background-color: #3b82f6;
    selection-color: white;
}
"""

# ==================== 进度条样式 ====================

PROGRESS_BAR_STYLE = """
QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 10px;
    height: 20px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 10px;
}
"""

# ==================== 标签样式 ====================

LABEL_TITLE = "color:#f1f5f9; font-size:18px; font-weight:700;"
LABEL_SUBTITLE = "color:#94a3b8; font-size:14px;"
LABEL_STATUS = "color:#f1f5f9; font-size:13px; font-weight:500;"
LABEL_DEVICE_COUNT = "color:#94a3b8; font-size:12px;"

# ==================== 复选框样式 ====================

CHECKBOX_STYLE = """
QCheckBox {
    color: #f1f5f9;
    font-size: 13px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #475569;
    border-radius: 4px;
    background-color: #1e293b;
}

QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
    image: url(none);
}

QCheckBox::indicator:hover {
    border-color: #64748b;
}
"""

# ==================== 文本框样式 ====================

TEXT_EDIT_STYLE = """
QTextEdit {
    background-color: #0f172a;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 12px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
}

QTextEdit:focus {
    border-color: #3b82f6;
}
"""

# ==================== 消息框样式 ====================

MESSAGE_BOX_SUCCESS = """
QLabel {
    background-color: #dcfce7;
    color: #166534;
    font-size: 14px;
    font-weight: 600;
    padding: 16px;
    border-radius: 8px;
}
"""

MESSAGE_BOX_WARNING = """
QLabel {
    background-color: #fef3c7;
    color: #92400e;
    font-size: 14px;
    font-weight: 600;
    padding: 16px;
    border-radius: 8px;
}
"""

MESSAGE_BOX_ERROR = """
QLabel {
    background-color: #fee2e2;
    color: #991b1b;
    font-size: 14px;
    font-weight: 600;
    padding: 16px;
    border-radius: 8px;
}
"""

# ==================== 工具函数 ====================

def get_color_scheme(purpose: str) -> dict:
    """
    获取特定用途的配色方案

    Args:
        purpose: 用途类型 ('primary', 'success', 'danger', 'warning', 'info')

    Returns:
        包含颜色的字典
    """
    schemes = {
        'primary': {'bg': '#3b82f6', 'hover': '#2563eb', 'text': '#ffffff'},
        'success': {'bg': '#10b981', 'hover': '#059669', 'text': '#ffffff'},
        'danger': {'bg': '#ef4444', 'hover': '#dc2626', 'text': '#ffffff'},
        'warning': {'bg': '#f59e0b', 'hover': '#d97706', 'text': '#ffffff'},
        'info': {'bg': '#06b6d4', 'hover': '#0891b2', 'text': '#ffffff'},
    }
    return schemes.get(purpose, schemes['primary'])


def get_badge_style(color: str, font_size: int = 13) -> str:
    """
    生成徽章样式

    Args:
        color: 颜色代码
        font_size: 字体大小
    """
    return f"color:{color}; font-weight:600; background:#f1f5f9; padding:4px 8px; border-radius:4px; font-size:{font_size}px;"
