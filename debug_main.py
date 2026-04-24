"""Debug main with extensive logging"""
import sys
import os
import logging

# 设置详细的日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=== LLDP Analyzer Debug Start ===")

try:
    logger.info("Step 1: Platform check")
    from lldp.platform import get_platform_config, is_macos

    config = get_platform_config()
    logger.info(f"Platform: {config.os_type.value}")
    logger.info(f"Admin: {config.is_admin}")

    # Check scapy support
    supported, message = config.check_scapy_support()
    if not supported:
        logger.error(f"Scapy support failed: {message}")
        if is_macos():
            logger.error(config.get_permission_instructions())
        logger.error("Exiting due to platform check failure")
        sys.exit(1)
    else:
        logger.info(f"Scapy: {message}")

    logger.info("Step 2: Platform check passed")

    logger.info("Step 3: Importing UI")
    from ui.pro_window import main as pro_main
    logger.info("UI imported successfully")

    logger.info("Step 4: Starting main function")
    pro_main()

    logger.info("Step 5: Main function completed")

except Exception as e:
    logger.error(f"Fatal error: {e}", exc_info=True)
    logger.error("Application failed to start")

    # Keep console open on error
    import traceback
    traceback.print_exc()

    if os.name == 'nt':
        input("\nPress Enter to exit...")
    sys.exit(1)
