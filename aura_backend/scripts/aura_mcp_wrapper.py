#!/usr/bin/env python3
"""
Wrapper script for Aura MCP Server
==================================

This wrapper allows the FastMCP server to run properly in the background
as part of the Aura backend system.
"""

import sys
import signal
import logging
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aura_mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Handle graceful shutdown
def signal_handler(sig, frame):
    logger.info("🛑 Received shutdown signal, stopping MCP server...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    try:
        # Import and run the MCP server
        from aura_server import mcp

        logger.info("🚀 Starting Aura MCP Server wrapper...")
        logger.info("🔗 Exposing Aura's capabilities via Model Context Protocol")

        # Run the MCP server (this will block)
        mcp.run()

    except Exception as e:
        logger.error("❌ Failed to start MCP server: %s", e)
        sys.exit(1)
