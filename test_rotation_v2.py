
import sys
from unittest.mock import MagicMock
from datetime import date, timedelta
import random

# Mocking the database collections
class MockCollection:
    def __init__(self, data):
        self.data = data
    
    def find(self, query=None, projection=None):
        # Return empty list for events to simulate no "existing" events in DB
        # unless we populate it
        return [] 

    def insert_many(self, events):
        pass
    
    def aggregate(self, pipeline):
        return []

# Create dummy app BEFORE importing shift_generator
app_mock = MagicMock()
# Setup mock users
users_data = [
    {"_id": str(i), "nombre": f"User{i}", "apellidos": "Test", "puesto": "TS", "skills": ["Flexibilidad", "Tarde", "Mail"], "visible_calendario": True, "fixed_shift_role": []}
    for i in range(1, 10)
]
app_mock.users_collection = MockCollection(users_data)
app_mock.events_collection = MockCollection([])
app_mock.es_dia_habil = lambda d: d.weekday() < 5
app_mock.FESTIVOS_DATES = set()

sys.modules["app"] = app_mock

# NOW import
from shift_generator import ShiftGenerator

def test_rotation():
    gen = ShiftGenerator(debug=False)
    # Inject users directly to skip fetch_data DB calls if needed, 
    # though with mock it should work.
    gen.users = users_data
    gen.existing_events = {}
    
    # Generate for Jan 2025
    print("Generating Jan 2025...")
    results = gen.generate(2025, 1)
    
    # Filter for Refuerzo
    refuerzos = [e for e in results if e["tipo"] == "Refuerzo Cade"]
    print(f"Total Refuerzo Events: {len(refuerzos)}")
    
    by_date = {}
    for r in refuerzos:
        by_date[r["fecha_inicio"]] = r["trabajador"]
        
    dates = sorted(by_date.keys())
    
    print("\n--- Daily Refuerzo Assignments ---")
    for d in dates:
        print(f"{d}: {by_date[d]}")
        
    # Analyze Consecutive Weeks
    print("\n--- Analysis ---")
    # Group by week number
    weeks = {}
    for d_str, user in by_date.items():
        dt = date.fromisoformat(d_str)
        week_num = dt.isocalendar()[1]
        if week_num not in weeks:
            weeks[week_num] = set()
        weeks[week_num].add(user)
        
    for w, users_set in sorted(weeks.items()):
        print(f"Week {w}: {users_set}")

if __name__ == "__main__":
    test_rotation()
