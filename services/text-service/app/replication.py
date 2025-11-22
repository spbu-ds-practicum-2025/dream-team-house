"""
Replication logic for distributed Text Service nodes
"""
import os
import aiohttp
import asyncio
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

NODE_ID = os.getenv("NODE_ID", "node-unknown")
NODE_NAME = os.getenv("NODE_NAME", "Unknown")
PEER_NODES = os.getenv("PEER_NODES", "").split(",") if os.getenv("PEER_NODES") else []
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://analytics-service:8000")


async def replicate_to_peers(version: int, text: str, timestamp: datetime, edit_id: Optional[str]):
    """
    Replicate document version to peer nodes asynchronously
    """
    if not PEER_NODES:
        logger.warning("No peer nodes configured for replication")
        return
    
    tasks = []
    for peer_url in PEER_NODES:
        if peer_url.strip():
            task = asyncio.create_task(
                replicate_to_node(peer_url.strip(), version, text, timestamp, edit_id)
            )
            tasks.append(task)
    
    # Wait for all replications with timeout
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def replicate_to_node(
    node_url: str,
    version: int,
    text: str,
    timestamp: datetime,
    edit_id: Optional[str]
):
    """
    Send replication message to a single node
    """
    url = f"{node_url}/api/replication/sync"
    payload = {
        "version": version,
        "text": text,
        "timestamp": timestamp.isoformat(),
        "edit_id": str(edit_id) if edit_id else None,
        "source_node": NODE_ID,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Replicated version {version} to {node_url}: {result}")
                    
                    # Send success event to analytics
                    await send_analytics_event({
                        "event_type": "replication_success",
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": {
                            "source_node": NODE_ID,
                            "target_node": node_url,
                        }
                    })
                else:
                    error_text = await response.text()
                    logger.error(f"Replication failed to {node_url}: {response.status} - {error_text}")
                    
                    # Send failure event to analytics
                    await send_analytics_event({
                        "event_type": "replication_failed",
                        "version": version,
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": {
                            "source_node": NODE_ID,
                            "target_node": node_url,
                            "error": error_text,
                            "status_code": response.status,
                        }
                    })
    except asyncio.TimeoutError:
        logger.error(f"Replication timeout to {node_url}")
        await send_analytics_event({
            "event_type": "replication_failed",
            "version": version,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "source_node": NODE_ID,
                "target_node": node_url,
                "error": "timeout",
            }
        })
    except Exception as e:
        logger.error(f"Replication error to {node_url}: {e}")
        await send_analytics_event({
            "event_type": "replication_failed",
            "version": version,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "source_node": NODE_ID,
                "target_node": node_url,
                "error": str(e),
            }
        })


async def send_analytics_event(event_data: dict):
    """
    Send event to Analytics Service
    """
    url = f"{ANALYTICS_URL}/api/analytics/events"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=event_data, timeout=aiohttp.ClientTimeout(total=3)) as response:
                if response.status not in [200, 201]:
                    logger.warning(f"Analytics event failed: {response.status}")
    except Exception as e:
        logger.warning(f"Failed to send analytics event: {e}")
