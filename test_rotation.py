
from shift_generator import ShiftGenerator
from datetime import date, timedelta
import random

# Mocking the database collections
class MockCollection:
    def __init__(self, data):
        self.data = data
    
    def find(self, query=None, projection=None):
        if query and "fecha_inicio" in query:
             return [] # Return empty existing events for now
        return self.data

    def insert_many(self, events):
        pass

# Setup mock users
users = [
    {"_id": str(i), "nombre": f"User{i}", "apellidos": "Test", "puesto": "TS", "skills": ["Flexibilidad"], "visible_calendario": True}
    for i in range(1, 10)
]

# user 1-2 have Flexibilidad, others don't for checking specific Refuerzo targeting
# Actually, the test script above gave everyone Flexibilidad.
# Let's verify who gets Refuerzo.

# We need to simulate the passage of weeks and see if assignments change.
# ShiftGenerator resets internal state (last_assignments) on Mondays.

def test_rotation():
    gen = ShiftGenerator(debug=False)
    gen.users = users
    # We need to bypass fetch_data to use our mock users
    # But generator.users is set directly above.
    
    # We need to mock existing_events to be empty
    gen.existing_events = {}
    
    # Generate for 3 weeks starting from a Monday
    start_date = date(2025, 1, 6) # Monday
    
    print(f"Testing Rotation starting {start_date}")
    
    previous_refuerzo = None
    streak_count = 0
    
    for i in range(21): # 3 weeks
        current_date = start_date + timedelta(days=i)
        
        # We need to fake "existing events" for that day (e.g. if someone is on vacation)
        # For this test, assume everyone is available.
        
        # We need to call generate logic for a SINGLE DAY or simulate it. 
        # The `generate` method loops over the whole month. 
        # It's easier to call `generate` for a month but we want to see week-by-week.
        pass

    # Actually, let's just run `generate` for a month and analyze the output.
    # The `generate` function clears last_assignments on Mondays.
    
    # We need to execute `generate` but capture its internal logic or output.
    # Since `generate` runs a loop, we can just run it for one month.
    
    gen.users = users 
    # Mocking app imports if they were used? 
    # usage of date.today in generating month?
    
    results = gen.generate(2025, 1) # Jan 2025
    
    # Filter for Refuerzo
    refuerzos = [e for e in results if e["tipo"] == "Refuerzo Cade"]
    print(f"Total Refuerzo Events: {len(refuerzos)}")
    
    by_date = {}
    for r in refuerzos:
        by_date[r["fecha_inicio"]] = r["trabajador"]
        
    dates = sorted(by_date.keys())
    for d in dates:
        print(f"{d}: {by_date[d]}")

if __name__ == "__main__":
    # Monkey patch modules that ShiftGenerator imports from app
    import sys
    from unittest.mock import MagicMock
    
    # Create a dummy app module
    app_mock = MagicMock()
    app_mock.users_collection = MockCollection(users)
    app_mock.events_collection = MockCollection([])
    app_mock.es_dia_habil = lambda d: d.weekday() < 5
    app_mock.FESTIVOS_DATES = set()
    
    sys.modules["app"] = app_mock
    
    # Now run test
    test_rotation()
