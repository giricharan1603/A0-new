"""
geocoder.py — Place name → GPS coordinates using Nominatim (OpenStreetMap).

No API key required. Respects Nominatim usage policy (1 req/sec).
Provides autocomplete suggestions and reverse geocoding.
"""

import time
import math
import threading
import requests
from typing import List, Dict, Optional, Tuple

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT     = "MITS-RealWorldRouter/1.0 (academic-project)"

# Simple in-process cache: key → (timestamp, result)
_cache: Dict[str, Tuple[float, list]] = {}
_cache_ttl   = 300.0   # seconds
_rate_lock   = threading.Lock()
_last_req_ts = 0.0


def _rate_limited_get(url: str, params: dict, timeout: int = 10) -> Optional[dict]:
    """HTTP GET with Nominatim 1-req/sec rate limiting."""
    global _last_req_ts
    with _rate_lock:
        gap = time.time() - _last_req_ts
        if gap < 1.05:
            time.sleep(1.05 - gap)
        try:
            resp = requests.get(
                url, params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            _last_req_ts = time.time()
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            _last_req_ts = time.time()
            raise RuntimeError(f"Nominatim request failed: {exc}") from exc


def geocode(query: str, limit: int = 5, country_codes: str = "") -> List[Dict]:
    """
    Convert a place name to a list of candidate GPS locations.

    Args:
        query:         Free-text place name, e.g. "Madhapalli", "Tirupati, AP"
        limit:         Max results to return (1–10).
        country_codes: Comma-separated ISO-3166-1 alpha-2 codes to bias search,
                       e.g. "in" for India. Empty = worldwide.

    Returns:
        List of dicts, each with keys:
            display_name, short_name, lat, lon, importance,
            bbox (south, north, west, east)
    """
    if not query or len(query.strip()) < 2:
        return []

    cache_key = f"fwd:{query.lower().strip()}:{limit}:{country_codes}"
    if cache_key in _cache:
        ts, cached = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return cached

    params = {
        "q":              query.strip(),
        "format":         "jsonv2",
        "limit":          min(max(limit, 1), 10),
        "addressdetails": 1,
        "extratags":      0,
        "namedetails":    0,
    }
    if country_codes:
        params["countrycodes"] = country_codes

    try:
        raw = _rate_limited_get(f"{NOMINATIM_BASE}/search", params)
    except RuntimeError:
        return []

    results = []
    for item in (raw or []):
        try:
            bb = item.get("boundingbox", [0, 0, 0, 0])
            # Nominatim returns [south, north, west, east] as strings
            results.append({
                "display_name": item.get("display_name", query),
                "short_name":   _make_short_name(item),
                "lat":          float(item["lat"]),
                "lon":          float(item["lon"]),
                "importance":   float(item.get("importance", 0.0)),
                "place_rank":   int(item.get("place_rank", 30)),
                "bbox": {
                    "south": float(bb[0]),
                    "north": float(bb[1]),
                    "west":  float(bb[2]),
                    "east":  float(bb[3]),
                },
            })
        except (KeyError, ValueError, IndexError):
            continue

    _cache[cache_key] = (time.time(), results)
    return results


def reverse_geocode(lat: float, lon: float) -> Optional[Dict]:
    """
    Convert GPS coordinates back to a place name.

    Returns a dict with keys: display_name, short_name, lat, lon
    """
    cache_key = f"rev:{lat:.5f}:{lon:.5f}"
    if cache_key in _cache:
        ts, cached = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return cached[0] if cached else None

    params = {
        "lat":    lat,
        "lon":    lon,
        "format": "jsonv2",
        "zoom":   16,
    }
    try:
        raw = _rate_limited_get(f"{NOMINATIM_BASE}/reverse", params)
    except RuntimeError:
        return None

    if not raw or "error" in raw:
        return None

    result = {
        "display_name": raw.get("display_name", f"{lat:.4f}, {lon:.4f}"),
        "short_name":   _make_short_name(raw),
        "lat":          float(raw.get("lat", lat)),
        "lon":          float(raw.get("lon", lon)),
    }
    _cache[cache_key] = (time.time(), [result])
    return result


def _make_short_name(item: dict) -> str:
    """Build a human-readable short name from a Nominatim address dict."""
    addr = item.get("address", {})
    parts = []

    # Priority: village/town/city → state_district → state → country
    for key in ("village", "suburb", "town", "city", "municipality",
                "county", "state_district", "state", "country"):
        val = addr.get(key)
        if val and val not in parts:
            parts.append(val)
        if len(parts) >= 3:
            break

    if parts:
        return ", ".join(parts)

    # Fallback: first 60 chars of display_name
    name = item.get("display_name", "Unknown")
    return name[:60] + ("…" if len(name) > 60 else "")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two GPS points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
