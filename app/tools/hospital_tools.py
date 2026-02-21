"""Hospital and medical-shop helper tools (app-level implementation).

This mirrors the previous implementation but lives under `app.tools`.
"""
from __future__ import annotations

import csv
import math
import os
from typing import Dict, Any, List, Tuple, Optional

import requests

from app.utils.geo import google_earth_link


DATA_CSV = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "chennai_hospitals_dshm.csv"))


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _geocode_address(address: str) -> Optional[Tuple[float, float]]:
    api_key = os.environ.get("GOOGLE_MAPS_KEY")
    if not api_key:
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return float(loc["lat"]), float(loc["lng"])
    return None


def _load_hospitals(csv_path: str) -> List[Dict[str, Any]]:
    hospitals = []
    try:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    row_lat = float(row.get("Latitude", 0) or 0)
                    row_lng = float(row.get("Longitude", 0) or 0)
                except Exception:
                    continue
                row["Latitude"] = row_lat
                row["Longitude"] = row_lng
                hospitals.append(row)
    except FileNotFoundError:
        alt = os.path.join(os.getcwd(), "src", "chennai_hospitals_dshm.csv")
        if alt != csv_path and os.path.exists(alt):
            return _load_hospitals(alt)
    return hospitals


def find_nearest_hospital(
    address: str,
    google_api_key: str,
    user_lat: float | None = None,
    user_lng: float | None = None,
) -> Dict[str, Any]:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY is required")

    # Use pre-computed coordinates if available, otherwise geocode
    if user_lat is not None and user_lng is not None:
        coords = (user_lat, user_lng)
    else:
        coords = _geocode_address(address)

    if coords is None:
        return {"success": False, "error": "Could not geocode address"}

    user_lat_val, user_lng_val = coords

    hospitals = _load_hospitals(DATA_CSV)
    if not hospitals:
        return {"success": False, "error": "Hospital dataset not found"}

    nearest = None
    best_d = float("inf")
    for h in hospitals:
        d = _haversine(user_lat_val, user_lng_val, h["Latitude"], h["Longitude"])
        if d < best_d:
            best_d = d
            nearest = h

    eta_minutes = (best_d / 30.0) * 60.0
    earth_link = google_earth_link(user_lat_val, user_lng_val)

    return {
        "success": True,
        "user_coords": {"lat": user_lat_val, "lng": user_lng_val},
        "nearest": nearest,
        "distance_km": round(best_d, 3),
        "eta_minutes": int(round(eta_minutes)),
        "earth_link": earth_link,
    }


def search_medical_shops_nearby(
    address: str,
    google_api_key: str,
    radius_m: int = 2000,
    user_lat: float | None = None,
    user_lng: float | None = None,
) -> Dict[str, Any]:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY is required")

    # Use pre-computed coordinates if available, otherwise geocode
    if user_lat is not None and user_lng is not None:
        lat, lng = user_lat, user_lng
    else:
        coords = _geocode_address(address)
        if coords is None:
            return {"success": False, "error": "Could not geocode address"}
        lat, lng = coords

    print(f"Searching for medical shops near {address} at coords ({lat}, {lng}) with radius {radius_m}m")

    # Using Google Places API Text Search (New) endpoint
    url = "https://places.googleapis.com/v1/places:searchText"
    body = {
        "textQuery": "pharmacy medical shop drugstore",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_m
            }
        },
        "openNow": True,
        "rankPreference": "DISTANCE",
        "pageSize": 10,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types,places.currentOpeningHours",
    }
    
    resp = requests.post(url, headers=headers, json=body, timeout=10)
    try:
        resp.raise_for_status()
    except Exception as e:
        return {"success": False, "error": f"Places API error: {resp.text}"}

    data = resp.json()
    results = data.get("places") or []
    print(f"Lat lng: ({lat}, {lng}), API returned {len(results)} places")
    return {"success": True, "user_coords": {"lat": lat, "lng": lng}, "places": results}
