"""
places_data.py - Curated dataset of popular cities, towns, villages, and landmarks
in Andhra Pradesh, Telangana, Karnataka, Tamil Nadu, and major Indian cities.
Provides instant, offline-reliable coordinate resolution and typo-tolerant search.
"""

import math as _math
from typing import Optional, Dict, Any, List

# Pre-indexed locations with precise coordinates and settlement type (village, town, city)
PLACES_DB = [
    # ── Madanapalle & Local Campus Hubs ──
    {
        "name": "Madanapalle",
        "type": "Town",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.5558,
        "lon": 78.5015,
        "aliases": ["madanapalle", "madanapalli", "mdp", "ma dea", "mada", "madana"]
    },
    {
        "name": "MITS Madanapalle Campus (Angallu)",
        "type": "Campus",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.633266,
        "lon": 78.479932,
        "aliases": ["mits", "mits madanapalle", "mits college", "angallu mits", "mits campus"]
    },
    {
        "name": "Angallu Village",
        "type": "Village",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6190,
        "lon": 78.4980,
        "aliases": ["angallu", "angallu village", "angalu"]
    },
    {
        "name": "Kurabalakota Village",
        "type": "Village",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6496,
        "lon": 78.4839,
        "aliases": ["kurabalakota", "kurbalakota"]
    },
    {
        "name": "Horsley Hills",
        "type": "Hill Station",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6500,
        "lon": 78.3900,
        "aliases": ["horsley hills", "horsely hills", "horsley", "yenugu mallamma konda"]
    },
    {
        "name": "Thettu Village",
        "type": "Village",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6650,
        "lon": 78.5300,
        "aliases": ["thettu"]
    },
    {
        "name": "Ghattu Village",
        "type": "Village",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6780,
        "lon": 78.4200,
        "aliases": ["ghattu"]
    },
    {
        "name": "B.Kothakota",
        "type": "Town",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.7225,
        "lon": 78.2936,
        "aliases": ["b.kothakota", "kothakota", "beerangi kothakota"]
    },
    {
        "name": "Tamballapalle",
        "type": "Town",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.8340,
        "lon": 78.4260,
        "aliases": ["tamballapalle", "thamballapalle"]
    },

    # ── Madanapalle → Tirupati Corridor Settlements ──
    {
        "name": "Valmikipuram (Vayalpad)",
        "type": "Town",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6500,
        "lon": 78.6333,
        "aliases": ["valmikipuram", "vayalpad", "voyalpad"]
    },
    {
        "name": "Kalikiri",
        "type": "Town",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6931,
        "lon": 78.7845,
        "aliases": ["kalikiri", "kalikiri town"]
    },
    {
        "name": "Pileru Town",
        "type": "Town",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6493,
        "lon": 78.9389,
        "aliases": ["pileru", "piler", "pileru town"]
    },
    {
        "name": "Rompicherla",
        "type": "Village",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6650,
        "lon": 79.0550,
        "aliases": ["rompicherla"]
    },
    {
        "name": "Pulicherla",
        "type": "Village",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6210,
        "lon": 79.0830,
        "aliases": ["pulicherla"]
    },
    {
        "name": "Damalcheruvu",
        "type": "Village",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.4833,
        "lon": 79.1167,
        "aliases": ["damalcheruvu"]
    },
    {
        "name": "Pakala Town",
        "type": "Town",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.4560,
        "lon": 79.1170,
        "aliases": ["pakala", "pakala junction"]
    },
    {
        "name": "Bhakarapeta",
        "type": "Village",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6700,
        "lon": 79.1830,
        "aliases": ["bhakarapeta", "bakrapet", "bakerapeta"]
    },
    {
        "name": "Chandragiri",
        "type": "Town",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.5833,
        "lon": 79.3167,
        "aliases": ["chandragiri", "chandragiri fort"]
    },
    {
        "name": "Srinivasa Mangapuram",
        "type": "Village",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6167,
        "lon": 79.3333,
        "aliases": ["srinivasa mangapuram"]
    },
    {
        "name": "Tirupati",
        "type": "City",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6316,
        "lon": 79.4232,
        "aliases": ["tirupati", "tirupathi", "tiru", "tirup", "tp", "tpt"]
    },
    {
        "name": "Renigunta",
        "type": "Town",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6500,
        "lon": 79.5167,
        "aliases": ["renigunta", "renigunta junction"]
    },
    {
        "name": "Tirumala",
        "type": "Town",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6833,
        "lon": 79.3500,
        "aliases": ["tirumala", "tirumala temple", "balaji"]
    },

    # ── Madanapalle → Chittoor / Palamaner Corridor ──
    {
        "name": "Punganur",
        "type": "Town",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.3667,
        "lon": 78.5833,
        "aliases": ["punganur", "punganuru"]
    },
    {
        "name": "Chowdepalle",
        "type": "Village",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.4167,
        "lon": 78.6833,
        "aliases": ["chowdepalle", "chowdepalli"]
    },
    {
        "name": "Somala",
        "type": "Village",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.4833,
        "lon": 78.7833,
        "aliases": ["somala"]
    },
    {
        "name": "Palamaner",
        "type": "Town",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.2000,
        "lon": 78.7500,
        "aliases": ["palamaner", "palamaneru"]
    },
    {
        "name": "Bangarupalem",
        "type": "Town",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.2167,
        "lon": 78.9333,
        "aliases": ["bangarupalem"]
    },
    {
        "name": "Chittoor",
        "type": "City",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.2172,
        "lon": 79.1003,
        "aliases": ["chittoor", "chittor", "ctr"]
    },

    # ── Madanapalle → Kadapa Corridor ──
    {
        "name": "Gurramkonda",
        "type": "Village",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.7833,
        "lon": 78.5833,
        "aliases": ["gurramkonda", "gurramkonda fort"]
    },
    {
        "name": "Rayachoti",
        "type": "City",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.0560,
        "lon": 78.7520,
        "aliases": ["rayachoti", "rayachoty"]
    },
    {
        "name": "Guvvalacheruvu",
        "type": "Village",
        "district": "YSR District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.2833,
        "lon": 78.7833,
        "aliases": ["guvvalacheruvu"]
    },
    {
        "name": "Kadapa (Cuddapah)",
        "type": "City",
        "district": "YSR District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.4673,
        "lon": 78.8242,
        "aliases": ["kadapa", "cuddapah", "kdp"]
    },
    {
        "name": "Rajampet",
        "type": "Town",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.1867,
        "lon": 79.1600,
        "aliases": ["rajampet", "rajampeta"]
    },

    # ── Madanapalle → Bengaluru Corridor ──
    {
        "name": "Chintamani",
        "type": "City",
        "district": "Chikkaballapur District",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.4000,
        "lon": 78.0667,
        "aliases": ["chintamani"]
    },
    {
        "name": "Srinivaspur",
        "type": "Town",
        "district": "Kolar District",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.3333,
        "lon": 78.2167,
        "aliases": ["srinivaspur", "srinivaspura"]
    },
    {
        "name": "Kolar",
        "type": "City",
        "district": "Kolar District",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.1367,
        "lon": 78.1292,
        "aliases": ["kolar", "kgf"]
    },
    {
        "name": "Hoskote",
        "type": "Town",
        "district": "Bengaluru Rural",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.0700,
        "lon": 77.7980,
        "aliases": ["hoskote", "hosakote"]
    },
    {
        "name": "Whitefield",
        "type": "City Suburb",
        "district": "Bengaluru Urban",
        "state": "Karnataka",
        "country": "India",
        "lat": 12.9698,
        "lon": 77.7500,
        "aliases": ["whitefield", "itpl"]
    },
    {
        "name": "Bengaluru (Bangalore)",
        "type": "Metro City",
        "district": "Bengaluru Urban",
        "state": "Karnataka",
        "country": "India",
        "lat": 12.9716,
        "lon": 77.5946,
        "aliases": ["bengaluru", "bangalore", "blr"]
    },
    {
        "name": "Kempegowda Int'l Airport (BLR)",
        "type": "Airport Hub",
        "district": "Bengaluru",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.1986,
        "lon": 77.7066,
        "aliases": ["bangalore airport", "blr airport", "kempegowda airport"]
    },

    # ── Tamil Nadu Hubs ──
    {
        "name": "Vellore",
        "type": "City",
        "district": "Vellore District",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 12.9165,
        "lon": 79.1325,
        "aliases": ["vellore", "vit vellore"]
    },
    {
        "name": "Ranipet",
        "type": "Town",
        "district": "Ranipet District",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 12.9272,
        "lon": 79.3331,
        "aliases": ["ranipet"]
    },
    {
        "name": "Kanchipuram",
        "type": "City",
        "district": "Kanchipuram District",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 12.8342,
        "lon": 79.7036,
        "aliases": ["kanchipuram", "conjeevaram"]
    },
    {
        "name": "Sriperumbudur",
        "type": "Town",
        "district": "Kanchipuram District",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 12.9720,
        "lon": 79.9460,
        "aliases": ["sriperumbudur"]
    },
    {
        "name": "Chennai",
        "type": "Metro City",
        "district": "Chennai District",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 13.0827,
        "lon": 80.2707,
        "aliases": ["chennai", "madras", "mas"]
    },

    # ── Major Regional Cities ──
    {
        "name": "Anantapur",
        "type": "City",
        "district": "Anantapur District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.6819,
        "lon": 77.6006,
        "aliases": ["anantapur", "anantapuram", "atp"]
    },
    {
        "name": "Kurnool",
        "type": "City",
        "district": "Kurnool District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 15.8281,
        "lon": 78.0373,
        "aliases": ["kurnool", "kurnoolu"]
    },
    {
        "name": "Nellore",
        "type": "City",
        "district": "SPSR Nellore District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.4426,
        "lon": 79.9865,
        "aliases": ["nellore", "nelluru"]
    },
    {
        "name": "Vijayawada",
        "type": "City",
        "district": "NTR District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 16.5062,
        "lon": 80.6480,
        "aliases": ["vijayawada", "bezawada", "vja"]
    },
    {
        "name": "Hyderabad",
        "type": "Metro City",
        "district": "Hyderabad District",
        "state": "Telangana",
        "country": "India",
        "lat": 17.3850,
        "lon": 78.4867,
        "aliases": ["hyderabad", "secunderabad", "hyd"]
    }
]


# ─────────────────────────────────────────────────────────────────────────────
# SPATIAL UTILITY
# ─────────────────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = _math.radians(lat1), _math.radians(lat2)
    dphi = _math.radians(lat2 - lat1)
    dlam = _math.radians(lon2 - lon1)
    a = _math.sin(dphi / 2)**2 + _math.cos(phi1) * _math.cos(phi2) * _math.sin(dlam / 2)**2
    return R * 2 * _math.atan2(_math.sqrt(max(0.0, a)), _math.sqrt(max(0.0, 1.0 - a)))


def nearest_place(lat: float, lon: float, radius_km: float = 12.0) -> Optional[str]:
    """Return the name of the nearest place in PLACES_DB within radius_km, or None."""
    best_name = None
    best_dist = float("inf")
    for p in PLACES_DB:
        d = _haversine_km(lat, lon, p["lat"], p["lon"])
        if d < best_dist and d <= radius_km:
            best_dist = d
            best_name = p["name"]
    return best_name


def nearest_place_info(lat: float, lon: float, radius_km: float = 18.0) -> Optional[dict]:
    """Return the detailed place dict of the nearest place in PLACES_DB within radius_km."""
    best_place = None
    best_dist = float("inf")
    for p in PLACES_DB:
        d = _haversine_km(lat, lon, p["lat"], p["lon"])
        if d < best_dist and d <= radius_km:
            best_dist = d
            best_place = {**p, "distance_km": round(d, 2)}
    return best_place
