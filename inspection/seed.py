"""Seed the database with the example truck/yard inspection checklist
(based on the GURMAN TRUCKING example PDF).

Run once:  python -m inspection.seed
"""

from . import db

# (section name, [(item name, item_type, require_photo), ...])
CHECKLIST = [
    ("PRE-CHECK", [
        ("Unit Number", "text", False),
        ("Driver Name", "text", False),
        ("Dashboard Picture", "pass_fail", True),
        ("Odometer", "text", True),
        ("Fuel Level", "text", False),
        ("DEF Level", "text", False),
    ]),
    ("INTERIOR", [
        ("Windshield Interior", "pass_fail", False),
        ("Camera", "yes_no", False),
        ("Bestpass", "pass_fail", False),
        ("ELD", "pass_fail", False),
        ("Fridge", "pass_fail", False),
        ("Microwave", "pass_fail", False),
        ("Mattress", "pass_fail", False),
        ("Fire Extinguisher", "pass_fail", False),
        ("Chains", "yes_no", False),
        ("Safety Triangles", "yes_no", False),
        ("VIN Number", "pass_fail", False),
        ("IFTA", "pass_fail", False),
    ]),
    ("EXTERIOR DS", [
        ("NY sticker", "pass_fail", False),
        ("HD lock", "yes_no", False),
        ("Inverter", "yes_no", False),
        ("Company Sticker", "yes_no", False),
        ("Bumper (Front)", "pass_fail", True),
        ("Hood Mirror DS", "pass_fail", False),
        ("Driver side truck", "pass_fail", False),
        ("Bumper DS", "pass_fail", False),
        ("Hood Mirror", "pass_fail", False),
        ("Side Mirror/Door/Cabwall DS", "pass_fail", False),
        ("Bracket Wind Deflector DS", "pass_fail", False),
        ("Top Spoiler", "pass_fail", False),
        ("Air Lines", "pass_fail", False),
        ("QF DS", "pass_fail", False),
        ("Rear Tires", "pass_fail", False),
        ("Mud Flap DS", "pass_fail", True),
        ("Tail lights (Back)", "pass_fail", False),
    ]),
    ("EXTERIOR PS", [
        ("Mud flap PS", "pass_fail", False),
        ("Rear Tires PS", "pass_fail", False),
        ("QF PS", "pass_fail", False),
        ("Bracket Wind Deflector PS", "pass_fail", False),
        ("Side Panel PS", "pass_fail", True),
        ("Step Fairing PS", "pass_fail", False),
        ("Door Mirror PS", "pass_fail", False),
        ("Headlight/Marker/Bumper/Hood", "pass_fail", False),
        ("Engine Condition", "pass_fail", False),
        ("Coolant Level", "pass_fail", False),
        ("Steer tire/Splash guard PS", "pass_fail", False),
        ("Steer tire/Splash guard DS", "pass_fail", False),
    ]),
]


def seed(place_name: str = "Yard Inspection (Truck)") -> int:
    db.init_db()

    # Avoid duplicating if it already exists
    for p in db.list_places():
        if p["name"] == place_name:
            print(f"Place '{place_name}' already exists (id={p['id']}). Skipping.")
            return p["id"]

    place_id = db.create_place(
        place_name,
        "Truck check-in / check-out inspection based on the example report.",
    )
    for section_name, items in CHECKLIST:
        section_id = db.create_section(place_id, section_name)
        for name, item_type, require_photo in items:
            db.create_item(section_id, name, item_type, require_photo)

    total = sum(len(items) for _, items in CHECKLIST)
    print(f"Seeded place '{place_name}' (id={place_id}) with "
          f"{len(CHECKLIST)} sections and {total} items.")
    return place_id


if __name__ == "__main__":
    seed()
