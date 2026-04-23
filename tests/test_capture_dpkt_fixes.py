"""
LLDP Capture DPkt - 专业代码审查修复验证测试

测试用户反馈的高优先级和中等优先级问题修复：
1. Scapy缺失检查
2. print替换为logger
3. 回调线程池机制
4. 重复nonlocal声明移除
5. 异常处理改进
6. stop_capture超时优化
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# 导入被测试的模块
from lldp.capture_dpkt import HybridCapture, HAS_SCAPY

pytestmark = pytest.mark.skipif(not HAS_SCAPY, reason="Scapy not available")


class TestScapyRequirement:
    """测试1：Scapy 缺失检查"""

    def test_requires_scapy(self):
        """验证 start_capture 在没有 Scapy 时抛出 RuntimeError"""
        capture = HybridCapture()
        interface = "eth0"

        # 模拟 HAS_SCAPY = False
        with patch('lldp.capture_dpkt.HAS_SCAPY', False):
            with pytest.raises(RuntimeError) as exc_info:
                capture.start_capture(interface, duration=1)

            # 验证错误消息包含提示
            assert "Scapy is required" in str(exc_info.value)
            assert "pip install scapy" in str(exc_info.value)


class TestLoggerUsage:
    """测试2：logger 使用验证"""

    def test_logger_instance_exists(self):
        """验证 logger 实例存在"""
        from lldp import capture_dpkt
        assert hasattr(capture_dpkt, 'log'), "应该有 log 实例"
        assert capture_dpkt.log.name == "lldp.capture_dpkt"

    def test_max_hex_display_defined(self):
        """验证 MAX_HEX_DISPLAY 常量定义"""
        from lldp import capture_dpkt
        assert hasattr(capture_dpkt, 'MAX_HEX_DISPLAY'), "应该定义 MAX_HEX_DISPLAY"
        assert capture_dpkt.MAX_HEX_DISPLAY == 200, "MAX_HEX_DISPLAY 应该是 200"

    def test_no_print_in_capture_dpkt(self):
        """验证 capture_dpkt.py 中没有 print 语句"""
        import inspect
        from lldp import capture_dpkt

        source = inspect.getsource(capture_dpkt)

        # 统计 print 语句数量
        print_count = source.count('print(')
        assert print_count == 0, f"发现 {print_count} 个 print 语句，应该使用 logger"


class TestCallbackThreadPool:
    """测试3：回调线程池机制"""

    def test_thread_pool_initialized(self):
        """验证线程池正确初始化"""
        capture = HybridCapture()

        assert hasattr(capture, '_callback_pool'), "应该有 _callback_pool 属性"
        assert isinstance(capture._callback_pool, ThreadPoolExecutor), \
            "_callback_pool 应该是 ThreadPoolExecutor 实例"

    def test_safe_callback_exists(self):
        """验证 _safe_callback 方法存在"""
        capture = HybridCapture()

        assert hasattr(capture, '_safe_callback'), "应该有 _safe_callback 方法"
        assert callable(capture._safe_callback), "_safe_callback 应该可调用"

    def test_callback_exception_handling(self):
        """验证回调异常被正确处理"""
        capture = HybridCapture()

        # 创建一个会抛出异常的 callback
        def failing_callback(device):
            raise ValueError("Test exception")

        # 创建一个 mock device
        mock_device = Mock()
        mock_device.is_valid.return_value = True

        # 调用 _safe_callback 应该捕获异常但不抛出
        try:
            capture._safe_callback(failing_callback, mock_device)
            # 如果到这里没有崩溃，说明异常处理正确
        except ValueError:
            pytest.fail("_safe_callback 应该捕获异常并记录，而不是重新抛出")


class TestExceptionHandling:
    """测试4和5：异常处理改进"""

    def test_log_exception_used(self):
        """验证使用 log.exception 记录异常"""
        import inspect
        from lldp import capture_dpkt

        source = inspect.getsource(capture_dpkt)

        # 检查是否使用 log.exception
        assert 'log.exception' in source, "应该使用 log.exception 记录异常"


class TestStopCaptureTimeout:
    """测试6：stop_capture 超时优化"""

    def test_stop_capture_increased_timeout(self):
        """验证 stop_capture 的超时时间增加到5秒"""
        import inspect
        source = inspect.getsource(HybridCapture.stop_capture)

        # 验证超时时间从2秒改为5秒
        assert 'join(timeout=5)' in source, \
            "stop_capture 的超时时间应该是5秒"

    def test_shutdown_method_exists(self):
        """验证 shutdown 方法存在"""
        capture = HybridCapture()

        assert hasattr(capture, 'shutdown'), "应该有 shutdown 方法"
        assert callable(capture.shutdown), "shutdown 应该可调用"


class TestNoDuplicateNonlocal:
    """测试7：重复 nonlocal 声明移除"""

    def test_no_duplicate_nonlocal(self):
        """验证没有重复的 nonlocal 声明"""
        import inspect
        source = inspect.getsource(HybridCapture._capture_worker)

        # 检查是否在 packet_handler 开头统一声明
        # 应该有：nonlocal packet_count, device_found
        assert 'nonlocal packet_count, device_found' in source, \
            "应该在 packet_handler 开头统一声明 nonlocal"

        # 统计 nonlocal 声明次数（应该只有一次）
        lines = source.split('\n')
        nonlocal_count = sum(1 for line in lines if 'nonlocal' in line)

        # 应该只有一行 nonlocal 声明
        assert nonlocal_count == 1, \
            f"nonlocal 应该只声明一次，发现 {nonlocal_count} 次"


class TestCaptureResultTyping:
    """测试8：CaptureResult 类型注解"""

    def test_capture_result_has_typing(self):
        """验证 CaptureResult 有类型注解"""
        from lldp.capture_dpkt import CaptureResult
        from dataclasses import fields

        # 检查字段是否存在
        field_names = [f.name for f in fields(CaptureResult)]
        assert 'device' in field_names
        assert 'timestamp' in field_names
        assert 'interface' in field_names


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '--tb=short'])
