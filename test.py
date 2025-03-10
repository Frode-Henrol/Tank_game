import json


units = {
    "tank1" : {
        "tank_speed_modifer" : 1,
        "projectile_speed_modifier" : 2,
        "firerate" : 2,
        "bounch_limit" : 2,
        "ai_personality" : "test"
    }
    
}



with open("test_units.json", "w") as f:
    json.dump(units, f, indent=4)
    
    
with open("test_data.json", "r") as f:
    
    data = json.load(f)
    
    
print(data)
