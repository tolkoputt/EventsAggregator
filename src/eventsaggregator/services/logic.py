def is_valid_seat(seats_pattern: str, seat: str) -> bool:
    parts = seats_pattern.split(",")
    for part in parts:
        start, count_seat = part.split("-")
        letter = start[0]
        if letter == seat[0] and int(seat[1:]) <= int(count_seat):
            return True
    return False
