
from dotenv.main import logger
import requests


def google_earth_link(lat, lon, altitude=100, heading=0, tilt=45, range_=0):
    """
    Generate a Google Earth Web link for given coordinates.
    Parameters:
        lat, lon: Coordinates
        altitude: Altitude in meters (default 100)
        heading: Rotation angle (default 0)
        tilt: Tilt angle (default 45)
        range_: Camera range (default 0)
    Returns:
        str: Google Earth link
    """
    return f"https://earth.google.com/web/@{lat},{lon},{altitude}a,{range_}d,{tilt}y,{heading}h,0t,0r"


def geocode_address(address: str, google_api_key: str) -> tuple[float, float] | None:
    """Geocode an address to get latitude and longitude."""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": google_api_key}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        logger.error("Geocoding API error", status_code=response.status_code, response_text=response.text)
        return None

    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        logger.warning("Geocoding failed", status=data.get("status"), results=data.get("results"))
        return None

    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]
