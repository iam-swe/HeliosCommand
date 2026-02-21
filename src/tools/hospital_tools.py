"""Compatibility wrapper re-exporting app-level hospital & places helpers."""
from app.tools.hospital_tools import find_nearest_hospital, search_medical_shops_nearby

__all__ = ["find_nearest_hospital", "search_medical_shops_nearby"]
