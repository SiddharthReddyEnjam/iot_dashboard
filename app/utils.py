def parse_gps_coord(coord_str):
    val = float(coord_str)
    degrees = int(val / 100)
    minutes = val - (degrees * 100)
    return degrees + (minutes / 60)
