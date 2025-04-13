import json


with open(r"units\units.json", "r") as json_file:
    all_units_data_json: dict = json.load(json_file)
    print(f"Loaded unit dict: {all_units_data_json}")
    
    
print(all_units_data_json[0])