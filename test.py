import json


dic = {"Test1" : 4000, "Test2" : 6000, "Unit_list" : [[1,2,3,4,5,6,7,8],[1,2,3,4,5,6,7,8]]}

print(dic)



with open("test_data.json", "w") as f:
    json.dump(dic, f, indent=4)
    
    
with open("test_data.json", "r") as f:
    
    data = json.load(f)
    
    
print(data)
