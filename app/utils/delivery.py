# import math

# def haversine_km(lat1, lon1, lat2, lon2):
#     # degrees -> radians
#     R = 6371.0
#     phi1, phi2 = math.radians(lat1), math.radians(lat2)
#     dphi = math.radians(lat2 - lat1)
#     dlambda = math.radians(lon2 - lon1)
#     a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
#     c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
#     return R * c


from app.models import DeliveryZone

def get_delivery_fee(address: str) -> int:
    """
    Return delivery fee in Naira.
    Falls back to ₦500 if no keyword matches.
    """
    if not address:
        return 500
    address = address.lower()
    zones   = DeliveryZone.query.all()
    for z in zones:
        if z.name.lower() in address:
            return z.fee
    return 500          # default