"""
places_data.py - Curated dataset of popular cities, towns, villages, and landmarks
in Andhra Pradesh, Telangana, Karnataka, Tamil Nadu, and major Indian cities.
Provides instant, offline-reliable coordinate resolution and typo-tolerant search.
"""

# Pre-indexed popular locations with precise coordinates
PLACES_DB = [
    # Rayalaseema & Chittoor / Annamayya District (Core area for MITS)
    {
        "name": "Madanapalle",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.5558,
        "lon": 78.5015,
        "aliases": ["madanapalle", "madanapalli", "mdp", "ma dea", "mada", "madana"]
    },
    {
        "name": "MITS Madanapalle Campus (Angallu)",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6281,
        "lon": 78.5015,
        "aliases": ["mits", "mits madanapalle", "mits college", "angallu mits", "mits campus"]
    },
    {
        "name": "Tirupati",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6316,
        "lon": 79.4232,
        "aliases": ["tirupati", "tirupathi", "tiru", "tirup", "tp", "tpt"]
    },
    {
        "name": "Tirumala",
        "district": "Tirupati District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6833,
        "lon": 79.3500,
        "aliases": ["tirumala", "tirumala temple", "balaji"]
    },
    {
        "name": "Angallu",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6190,
        "lon": 78.4980,
        "aliases": ["angallu", "angallu village", "angalu"]
    },
    {
        "name": "Horsley Hills",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.6500,
        "lon": 78.3900,
        "aliases": ["horsley hills", "horsely hills", "horsley", "yenugu mallamma konda"]
    },
    {
        "name": "Punganur",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.3667,
        "lon": 78.5833,
        "aliases": ["punganur", "punganuru"]
    },
    {
        "name": "Chittoor",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.2172,
        "lon": 79.1003,
        "aliases": ["chittoor", "chittor", "ctr"]
    },
    {
        "name": "Palamaner",
        "district": "Chittoor District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.2000,
        "lon": 78.7500,
        "aliases": ["palamaner", "palamaneru"]
    },
    {
        "name": "Kadapa (Cuddapah)",
        "district": "YSR District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.4673,
        "lon": 78.8242,
        "aliases": ["kadapa", "cuddapah", "kdp"]
    },
    {
        "name": "Rayachoti",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.0560,
        "lon": 78.7520,
        "aliases": ["rayachoti", "rayachoty"]
    },
    {
        "name": "Rajampet",
        "district": "Annamayya District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.1867,
        "lon": 79.1600,
        "aliases": ["rajampet", "rajampeta"]
    },
    {
        "name": "Anantapur",
        "district": "Anantapur District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.6819,
        "lon": 77.6006,
        "aliases": ["anantapur", "anantapuram", "atp"]
    },
    {
        "name": "Hindupur",
        "district": "Sri Sathya Sai District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 13.8290,
        "lon": 77.4920,
        "aliases": ["hindupur", "hindupuram"]
    },
    {
        "name": "Kurnool",
        "district": "Kurnool District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 15.8281,
        "lon": 78.0373,
        "aliases": ["kurnool", "kurnoolu"]
    },
    {
        "name": "Nellore",
        "district": "SPSR Nellore District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 14.4426,
        "lon": 79.9865,
        "aliases": ["nellore", "nelluru"]
    },
    {
        "name": "Vijayawada",
        "district": "NTR District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 16.5062,
        "lon": 80.6480,
        "aliases": ["vijayawada", "bezawada", "vja"]
    },
    {
        "name": "Guntur",
        "district": "Guntur District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 16.3067,
        "lon": 80.4365,
        "aliases": ["guntur", "gnt"]
    },
    {
        "name": "Visakhapatnam (Vizag)",
        "district": "Visakhapatnam District",
        "state": "Andhra Pradesh",
        "country": "India",
        "lat": 17.6868,
        "lon": 83.2185,
        "aliases": ["visakhapatnam", "vizag", "waltair"]
    },
    # Karnataka Hubs nearby
    {
        "name": "Bengaluru (Bangalore)",
        "district": "Bengaluru Urban",
        "state": "Karnataka",
        "country": "India",
        "lat": 12.9716,
        "lon": 77.5946,
        "aliases": ["bengaluru", "bangalore", "blr"]
    },
    {
        "name": "Kempegowda Int'l Airport (BLR)",
        "district": "Bengaluru",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.1986,
        "lon": 77.7066,
        "aliases": ["bangalore airport", "blr airport", "kempegowda airport"]
    },
    {
        "name": "Kolar",
        "district": "Kolar District",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.1367,
        "lon": 78.1292,
        "aliases": ["kolar", "kgf"]
    },
    {
        "name": "Chintamani",
        "district": "Chikkaballapur District",
        "state": "Karnataka",
        "country": "India",
        "lat": 13.4000,
        "lon": 78.0667,
        "aliases": ["chintamani"]
    },
    {
        "name": "Mysuru (Mysore)",
        "district": "Mysuru District",
        "state": "Karnataka",
        "country": "India",
        "lat": 12.2958,
        "lon": 76.6394,
        "aliases": ["mysore", "mysuru"]
    },
    # Tamil Nadu Hubs nearby
    {
        "name": "Chennai",
        "district": "Chennai District",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 13.0827,
        "lon": 80.2707,
        "aliases": ["chennai", "madras", "mas"]
    },
    {
        "name": "Vellore",
        "district": "Vellore District",
        "state": "Tamil Nadu",
        "country": "India",
        "lat": 12.9165,
        "lon": 79.1325,
        "aliases": ["vellore", "vit vellore"]
    },
    # Telangana
    {
        "name": "Hyderabad",
        "district": "Hyderabad District",
        "state": "Telangana",
        "country": "India",
        "lat": 17.3850,
        "lon": 78.4867,
        "aliases": ["hyderabad", "secunderabad", "hyd"]
    },
    {
        "name": "Warangal",
        "district": "Warangal District",
        "state": "Telangana",
        "country": "India",
        "lat": 17.9689,
        "lon": 79.5941,
        "aliases": ["warangal", "hanamkonda"]
    }
]
