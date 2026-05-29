"""Real-world Indian agricultural statistics (Pan-India macro-anchored config).

Contains geographical coordinates, seasonal crop distributions, average landholding size,
soil types, and irrigation distributions for major agricultural states in India.
"""

STATE_MACRO_DATA = {
    "Punjab": {
        "weight": 0.18,
        "land_lognormal_mu": 1.2,       # Median land size ~3.3 acres (Larger average holdings)
        "land_lognormal_sigma": 0.6,
        "districts": {
            "Ludhiana": (30.9010, 75.8573),
            "Amritsar": (31.6340, 74.8723),
            "Patiala": (30.3398, 76.3869),
            "Bathinda": (30.2110, 74.9455),
            "Jalandhar": (31.3260, 75.5762),
        },
        "crops": {
            "Wheat": 0.50,
            "Rice": 0.40,
            "Maize": 0.08,
            "Cotton": 0.02,
        },
        "soil_types": ["Alluvial", "Sandy Loam"],
        "irrigation_types": ["Canal", "Borewell"],
        "villages": ["Gill", "Halwara", "Khamanon", "Jandiala", "Ajnala", "Mullanpur"],
    },
    "Uttar Pradesh": {
        "weight": 0.25,
        "land_lognormal_mu": 0.3,       # Median land size ~1.3 acres (Small/marginal dominant)
        "land_lognormal_sigma": 0.7,
        "districts": {
            "Meerut": (28.9845, 77.7064),
            "Gorakhpur": (26.7606, 83.3731),
            "Varanasi": (25.3176, 82.9739),
            "Bareilly": (28.3670, 79.4304),
            "Lakhimpur": (27.9475, 80.7786),
        },
        "crops": {
            "Sugarcane": 0.40,
            "Wheat": 0.35,
            "Rice": 0.20,
            "Maize": 0.05,
        },
        "soil_types": ["Alluvial", "Red", "Sandy Loam"],
        "irrigation_types": ["Canal", "Borewell", "Drip"],
        "villages": ["Kalyanpur", "Shivpur", "Gopalpur", "Rampur", "Dharamputra"],
    },
    "Maharashtra": {
        "weight": 0.22,
        "land_lognormal_mu": 0.7,       # Median land size ~2.0 acres
        "land_lognormal_sigma": 0.75,
        "districts": {
            "Pune": (18.5204, 73.8567),
            "Nashik": (19.9975, 73.7898),
            "Nagpur": (21.1458, 79.0882),
            "Kolhapur": (16.7050, 74.2433),
            "Jalgaon": (21.0077, 75.5626),
        },
        "crops": {
            "Soybean": 0.30,
            "Cotton": 0.25,
            "Sugarcane": 0.25,
            "Wheat": 0.10,
            "Rice": 0.05,
            "Maize": 0.05,
        },
        "soil_types": ["Black", "Red", "Laterite"],
        "irrigation_types": ["Rainfed", "Drip", "Borewell", "Canal"],
        "villages": ["Shivpura", "Khedgaon", "Basantwadi", "Devgaon", "Wadgaon"],
    },
    "Andhra Pradesh": {
        "weight": 0.18,
        "land_lognormal_mu": 0.5,       # Median land size ~1.6 acres
        "land_lognormal_sigma": 0.7,
        "districts": {
            "Guntur": (16.3067, 80.4365),
            "Nellore": (14.4426, 79.9865),
            "Kurnool": (15.8281, 78.0373),
            "East Godavari": (16.9891, 82.2475),
            "Anantapur": (14.6819, 77.6006),
        },
        "crops": {
            "Rice": 0.45,
            "Cotton": 0.25,
            "Maize": 0.20,
            "Soybean": 0.10,
        },
        "soil_types": ["Red", "Sandy Loam", "Black"],
        "irrigation_types": ["Canal", "Rainfed", "Borewell", "Drip"],
        "villages": ["Koppaka", "Peddapuram", "Maruteru", "Tenali", "Dharmavaram"],
    },
    "West Bengal": {
        "weight": 0.17,
        "land_lognormal_mu": -0.1,      # Median land size ~0.9 acres (Very small holdings)
        "land_lognormal_sigma": 0.6,
        "districts": {
            "Bardhaman": (23.2324, 87.8630),
            "Murshidabad": (24.1750, 88.2800),
            "Midnapore": (22.4257, 87.3199),
            "Hooghly": (22.9012, 88.3899),
            "Nadia": (23.4000, 88.5000),
        },
        "crops": {
            "Rice": 0.75,
            "Maize": 0.15,
            "Wheat": 0.10,
        },
        "soil_types": ["Alluvial", "Laterite", "Red"],
        "irrigation_types": ["Rainfed", "Canal", "Borewell"],
        "villages": ["Gopalganj", "Khatra", "Singur", "Katwa", "Palashi"],
    },
}

# Compile a global district mapping for fast lat-long lookups downstream
ALL_DISTRICT_CENTERS = {}
for state, info in STATE_MACRO_DATA.items():
    for dist, coords in info["districts"].items():
        ALL_DISTRICT_CENTERS[dist] = coords
