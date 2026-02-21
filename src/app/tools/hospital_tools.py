"""Hospital and medical-shop helper tools (app-level implementation).

This mirrors the previous implementation but lives under `app.tools`.
"""
from __future__ import annotations

import csv
import math
import os
from typing import Dict, Any, List, Tuple, Optional

import requests


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


def _geocode_address(address: str, api_key: str) -> Optional[Tuple[float, float]]:
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


def find_nearest_hospital(address: str, google_api_key: str) -> Dict[str, Any]:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY is required")

    coords = _geocode_address(address, google_api_key)
    if coords is None:
        return {"success": False, "error": "Could not geocode address"}

    user_lat, user_lng = coords

    hospitals = _load_hospitals(DATA_CSV)
    if not hospitals:
        return {"success": False, "error": "Hospital dataset not found"}

    nearest = None
    best_d = float("inf")
    for h in hospitals:
        d = _haversine(user_lat, user_lng, h["Latitude"], h["Longitude"])
        if d < best_d:
            best_d = d
            nearest = h

    eta_minutes = (best_d / 30.0) * 60.0

    return {
        "success": True,
        "user_coords": {"lat": user_lat, "lng": user_lng},
        "nearest": nearest,
        "distance_km": round(best_d, 3),
        "eta_minutes": int(round(eta_minutes)),
    }


def search_medical_shops_nearby(address: str, google_api_key: str, radius_m: int = 2000) -> Dict[str, Any]:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY is required")

    coords = _geocode_address(address, google_api_key)
    if coords is None:
        return {"success": False, "error": "Could not geocode address"}

    lat, lng = coords

    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = {
        "location": {"lat": lat, "lng": lng},
        "radius": radius_m,
        "query": "medical shop|pharmacy|medical store",
    }

    params = {"key": google_api_key}
    resp = requests.post(url, params=params, json=body, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        return {"success": False, "error": f"Places API error: {resp.text}"}

    data = resp.json()
    results = data.get("results") or data.get("candidates") or []
    return {"success": True, "user_coords": {"lat": lat, "lng": lng}, "places": results}
"""Wrapper module mirroring top-level tools for app package."""
from tools.hospital_tools import (
    find_nearest_hospital,
    search_medical_shops_nearby,
)

__all__ = ["find_nearest_hospital", "search_medical_shops_nearby"]
