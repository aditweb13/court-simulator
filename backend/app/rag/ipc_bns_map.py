"""Concordance mapping between Indian Penal Code (IPC) and Bharatiya Nyaya Sanhita (BNS).

Provides exact cross-referencing between historical IPC sections and their
counterparts in the modern Bharatiya Nyaya Sanhita (BNS, 2023).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_MAP_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "law_corpus" / "raw" / "ipc_bns_map.json"
)

_BNS_TO_IPC: Optional[Dict[str, str]] = None
_IPC_TO_BNS: Optional[Dict[str, str]] = None


def load_concordance_map(
    map_path: Optional[Path] = None,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Load and cache the concordance mapping tables between BNS and IPC."""
    global _BNS_TO_IPC, _IPC_TO_BNS

    if _BNS_TO_IPC is not None and _IPC_TO_BNS is not None and map_path is None:
        return _BNS_TO_IPC, _IPC_TO_BNS

    target_path = map_path or _DEFAULT_MAP_PATH
    if not target_path.exists():
        logger.warning("Concordance map file not found at %s", target_path)
        return {}, {}

    try:
        data = json.loads(target_path.read_text(encoding="utf-8"))
        bns_to_ipc = data.get("bns_to_ipc", {})
        ipc_to_bns = data.get("ipc_to_bns", {})
        if map_path is None:
            _BNS_TO_IPC = bns_to_ipc
            _IPC_TO_BNS = ipc_to_bns
        return bns_to_ipc, ipc_to_bns
    except Exception as exc:
        logger.error("Failed to parse concordance map from %s: %s", target_path, exc)
        return {}, {}


def get_ipc_equivalent(
    bns_section: str, map_path: Optional[Path] = None
) -> Optional[str]:
    """Retrieve corresponding IPC section for a given BNS section number."""
    bns_to_ipc, _ = load_concordance_map(map_path)
    # Strip any sub-part references or parentheses, e.g. "103 (Part 1/2)" -> "103"
    clean_sec = bns_section.split()[0].split("(")[0].strip()
    return bns_to_ipc.get(clean_sec)


def get_bns_equivalent(
    ipc_section: str, map_path: Optional[Path] = None
) -> Optional[str]:
    """Retrieve corresponding BNS section for a given IPC section number."""
    _, ipc_to_bns = load_concordance_map(map_path)
    clean_sec = ipc_section.split()[0].split("(")[0].strip()
    return ipc_to_bns.get(clean_sec)
