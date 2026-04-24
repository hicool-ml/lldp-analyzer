"""
Adapter to make Copilot's HybridCapture compatible with UI's LLDPCaptureListener interface

This adapter bridges the API differences between:
- UI expects: LLDPCaptureListener with start/stop methods
- Copilot provides: HybridCapture with start_capture/stop_capture methods
"""
import logging
from typing import Callable, Optional
from .capture_dpkt import HybridCapture

log = logging.getLogger("lldp.capture_adapter")


class LLDPCaptureListener:
    """
    Adapter class that makes HybridCapture compatible with UI expectations

    Provides the same interface as the stable version's LLDPCaptureListener:
    - start(interface, duration, on_device_discovered, on_capture_complete)
    - stop()
    - thread attribute for UI monitoring
    """

    def __init__(self):
        """Initialize the adapter with a HybridCapture instance"""
        self._hybrid_capture = HybridCapture()  # Internal capture instance
        self.thread = None  # UI expects this attribute
        self._interface = None
        self._duration = None
        self._on_device_discovered = None
        self._on_capture_complete = None

        # 🔥 关键修复：禁用Copilot版本的线程池，确保回调直接执行
        # UI使用QueuedConnection来确保线程安全，不需要额外的线程池
        if hasattr(self._hybrid_capture, '_callback_pool'):
            # 保存原始线程池但禁用它
            self._original_callback_pool = self._hybrid_capture._callback_pool
            self._hybrid_capture._callback_pool = None

    @property
    def _capture(self):
        """Property to provide access to internal capture for compatibility"""
        return self._hybrid_capture

    def start(self, interface, duration: int = 60,
             on_device_discovered: Optional[Callable] = None,
             on_capture_complete: Optional[Callable] = None):
        """
        Start LLDP/CDP capture (UI-compatible interface)

        Args:
            interface: Network interface object (from Scapy)
            duration: Capture duration in seconds
            on_device_discovered: Callback when device discovered
            on_capture_complete: Callback when capture completes
        """
        try:
            self._interface = interface
            self._duration = duration
            self._on_device_discovered = on_device_discovered
            self._on_capture_complete = on_capture_complete

            log.info(f"Starting capture on {interface.name} for {duration}s")

            # 🔥 关键修复：确保回调在主线程中执行，避免UI线程安全问题
            # Copilot版本使用线程池，但UI期望直接调用
            def device_callback(device):
                """Forward device discovery to UI callback (thread-safe)"""
                if on_device_discovered:
                    try:
                        # 🔥 直接调用UI回调，不使用线程池
                        # UI会通过QueuedConnection确保在主线程中执行
                        on_device_discovered(device)
                    except Exception as e:
                        log.exception(f"Device callback raised exception: {e}")

            # 🔥 禁用Copilot版本的线程池，直接调用回调
            # 这确保UI的信号槽机制能正常工作
            self._hybrid_capture._current_callback = device_callback

            # Start capture using HybridCapture
            self._hybrid_capture.start_capture(
                interface=interface,
                duration=duration,
                callback=device_callback
            )

            # Set thread attribute for UI monitoring
            if hasattr(self._hybrid_capture, 'capture_thread'):
                self.thread = self._hybrid_capture.capture_thread

            log.info("Capture started successfully")

        except Exception as e:
            log.exception(f"Failed to start capture: {e}")
            raise

    def stop(self):
        """Stop the capture (UI-compatible interface)"""
        try:
            log.info("Stopping capture")

            # 🔥 关键修复：先停止捕获，再调用回调，确保UI状态正确
            self._hybrid_capture.stop_capture()

            # Call capture complete callback if provided
            if self._on_capture_complete:
                try:
                    # Get discovered devices
                    devices = self._hybrid_capture.get_discovered_devices()
                    self._on_capture_complete(devices)
                except Exception as e:
                    log.exception("Capture complete callback raised exception")

            # Store thread reference for UI
            if hasattr(self._hybrid_capture, 'capture_thread'):
                self.thread = self._hybrid_capture.capture_thread

            log.info("Capture stopped successfully")

        except Exception as e:
            log.exception(f"Failed to stop capture: {e}")

    def get_discovered_devices(self):
        """Get list of discovered devices (convenience method)"""
        return self._hybrid_capture.get_discovered_devices()

    def is_active(self):
        """Check if capture is still active"""
        return self._hybrid_capture.is_active()


# For backwards compatibility, also provide direct access
HybridCaptureListener = LLDPCaptureListener
