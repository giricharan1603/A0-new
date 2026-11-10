"""
geocoder.py — Intelligent Multi-Layer Geocoding & Autocomplete Engine.

Layers:
1. Fast local database lookup (pre-indexed coordinates for key cities, towns & villages).
2. Advanced Typo-Tolerant & Fuzzy Matcher (handles queries like 'ma dea', 'mada', 'tirup', 'tiru').
3. Online Nominatim OpenStreetMap fallback with timeout guard & local caching.
"""

import time
import math
import re
import difflib
import threading
import requests
from typing import List, Dict, Optional, Tuple

from core.places_data import PLACES_DB

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT     = "MITS-RealWorldRouter-Pro/2.0 (student-project)"

_cache: Dict[str, Tuple[float, list]] = {}
_cache_ttl   = 3600.0   # 1 hour
_rate_lock   = threading.Lock()
_last_req_ts = 0.0


def _normalize(text: str) -> str:
    """Normalize text by stripping spaces, special chars, and lowercasing."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _search_local_places(query: str, limit: int = 5) -> List[Dict]:
    """
    Search curated PLACES_DB using prefix, token, and fuzzy similarity.
    Supports queries like 'ma dea' for Madanapalle, 'tirup' for Tirupati.
    """
    if not query or len(query.strip()) < 2:
        return []

    q_clean = _normalize(query)
    q_words = query.lower().split()

    scored_matches: List[Tuple[float, Dict]] = []

    for place in PLACES_DB:
        p_name_norm = _normalize(place["name"])
        p_aliases_norm = [_normalize(a) for a in place.get("aliases", [])]
        all_norm_names = [p_name_norm] + p_aliases_norm

        best_score = 0.0

        # Exact or alias match
        if q_clean in all_norm_names:
            best_score = 1.0
        else:
            # Prefix match
            for n in all_norm_names:
                if n.startswith(q_clean):
                    best_score = max(best_score, 0.95)
                elif q_clean in n:
                    best_score = max(best_score, 0.85)

            # Sub-word multi-token match (e.g. 'ma dea' -> 'ma' and 'dea')
            if best_score < 0.8:
                word_matches = 0
                for w in q_words:
                    w_norm = _normalize(w)
                    if any(w_norm in n for n in all_norm_names):
                        word_matches += 1
                if word_matches == len(q_words) and len(q_words) > 1:
                    best_score = max(best_score, 0.80)

            # Fuzzy similarity match
            if best_score < 0.7:
                for n in all_norm_names:
                    ratio = difflib.SequenceMatcher(None, q_clean, n).ratio()
                    # Also test against prefix of equivalent length
                    sub_ratio = difflib.SequenceMatcher(None, q_clean, n[:len(q_clean) + 2]).ratio()
                    best_score = max(best_score, ratio * 0.75, sub_ratio * 0.82)

        if best_score >= 0.55:
            display_name = f"{place['name']}, {place['district']}, {place['state']}, {place['country']}"
            short_name = f"{place['name']}, {place['state']}"
            scored_matches.append((
                best_score,
                {
                    "display_name": display_name,
                    "short_name": short_name,
                    "lat": place["lat"],
                    "lon": place["lon"],
                    "source": "verified_local",
                    "importance": best_score
                }
            ))

    scored_matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in scored_matches[:limit]]


def _rate_limited_nominatim_get(url: str, params: dict, timeout: int = 4) -> Optional[list]:
    """Execute rate-limited request to Nominatim API."""
    global _last_req_ts
    with _rate_lock:
        gap = time.time() - _last_req_ts
        if gap < 1.05:
            time.sleep(1.05 - gap)
        try:
            resp = requests.get(
                url, params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout
            )
            _last_req_ts = time.time()
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            _last_req_ts = time.time()
            return None
    return None


def geocode(query: str, limit: int = 5, country_codes: str = "in") -> List[Dict]:
    """
    Search places across both local high-priority dataset and online Nominatim.
    Always returns immediate results for popular destinations without hanging.
    """
    if not query or len(query.strip()) < 2:
        return []

    q_strip = query.strip()
    cache_key = f"geo:{q_strip.lower()}:{limit}:{country_codes}"

    if cache_key in _cache:
        ts, cached = _cache[cache_key]
        if time.time() - ts < _cache_ttl:
            return cached

    # 1. Search local verified database first
    local_results = _search_local_places(q_strip, limit=limit)
    if len(local_results) >= limit or (local_results and local_results[0].get("importance", 0) >= 0.85):
        _cache[cache_key] = (time.time(), local_results)
        return local_results

    # 2. Online search fallback (or complement)
    online_results = []
    params = {
        "q": q_strip,
        "format": "jsonv2",
        "limit": limit,
        "addressdetails": 1,
    }
    if country_codes:
        params["countrycodes"] = country_codes

    raw = _rate_limited_nominatim_get(f"{NOMINATIM_BASE}/search", params, timeout=3)
    if raw:
        for item in raw:
            try:
                lat = float(item["lat"])
                lon = float(item["lon"])
                addr = item.get("address", {})
                parts = [
                    addr.get("village") or addr.get("suburb") or addr.get("town") or addr.get("city") or item.get("name", ""),
                    addr.get("state_district") or addr.get("county", ""),
                    addr.get("state", ""),
                    addr.get("country", "")
                ]
                clean_parts = [p for p in parts if p]
                short_name = ", ".join(clean_parts[:2]) if clean_parts else item.get("display_name", "")[:45]

                online_results.append({
                    "display_name": item.get("display_name", ""),
                    "short_name": short_name,
                    "lat": lat,
                    "lon": lon,
                    "source": "nominatim_osm",
                    "importance": float(item.get("importance", 0.5))
                })
            except Exception:
                continue

    # Merge results (local first, then online)
    seen_coords = set()
    combined = []
    for item in local_results + online_results:
        key = (round(item["lat"], 3), round(item["lon"], 3))
        if key not in seen_coords:
            seen_coords.add(key)
            combined.append(item)

    combined = combined[:limit]
    _cache[cache_key] = (time.time(), combined)
    return combined


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometers between two GPS points."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
