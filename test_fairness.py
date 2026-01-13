
import sys
from unittest.mock import MagicMock
from datetime import date, timedelta
import random
from collections import Counter

# Mocking the database collections
class MockCollection:
    def __init__(self, data):
        self.data = data
    
    def find(self, query=None, projection=None):
        return [] 
    
    def insert_many(self, events):
        pass
    
    def aggregate(self, pipeline):
        return []

app_mock = MagicMock()
# Setup 5 users to check distribution among more than 2
users_data = [
    {"_id": str(i), "nombre": f"User{i}", "apellidos": "Test", "puesto": "TS", 
     "skills": ["Flexibilidad", "Tarde", "Mail"], # Everyone has all skills
     "visible_calendario": True, 
     "fixed_shift_role": []}
    for i in range(1, 6)
]

# Add a user with Fixed PIAS
users_data.append({
    "_id": "6", "nombre": "FixedPIAS", "apellidos": "User", "puesto": "TS",
    "skills": [], "visible_calendario": True,
    "fixed_shift_role": ["PIAS"]
})

app_mock.users_collection = MockCollection(users_data)
app_mock.events_collection = MockCollection([])
app_mock.es_dia_habil = lambda d: d.weekday() < 5
app_mock.FESTIVOS_DATES = set()

sys.modules["app"] = app_mock # Patch app

from shift_generator import ShiftGenerator

def test_fairness_and_pias():
    gen = ShiftGenerator(debug=False)
    gen.users = users_data
    gen.existing_events = {}
    
    # Generate for Jan 2025 (4 weeks roughly)
    # To really test fairness, maybe we need more time or multiple months?
    # Let's try 2 months to get significant counts.
    
    results = []
    print("Generating Jan 2025...")
    results.extend(gen.generate(2025, 1))
    
    # We need to preserve history? generate() clears daily history but keeps annual?
    # No, generate() re-initializes `tarde_count` from DB every time. 
    # Since we mock DB returning empty, subsequent calls to generate() will restart counts from 0 
    # unless we update our mock DB.
    # For this test, one month might be enough if we just check that it doesn't only pick 2 people.
    
    # Filter for Refuerzo
    refuerzos = [e for e in results if e["tipo"] == "Refuerzo Cade"]
    print(f"\nTotal Refuerzo Events: {len(refuerzos)}")
    
    counts = Counter(r["trabajador"] for r in refuerzos)
    print("Refuerzo Distribution:", counts)
    
    # Check Fairness: with 5 users and ~20 days, each should have ~4 days.
    # If 2 users have 10 each and others 0, it's unfair.
    
    users_with_assignments = len(counts)
    print(f"Unique users assigned Refuerzo: {users_with_assignments}/5")
    
    if users_with_assignments < 4:
         print("FAIL: Distribution is too concentrated (less than 4 unique users for 5 available).")
    else:
         print("PASS: Distribution covers most available users.")
    
    # Check Fixed PIAS
    pias_events = [e for e in results if e["trabajador"] == "FixedPIAS User"]
    print(f"Events for FixedPIAS User: {[e['tipo'] for e in pias_events]}")
    
    explicit_pias = [e for e in pias_events if e["tipo"] == "PIAS"]
    if explicit_pias:
        print("FAIL: Explicit PIAS events found for Fixed Shift user.")
    else:
        print("PASS: No explicit PIAS events for Fixed Shift user.")

if __name__ == "__main__":
    test_fairness_and_pias()
