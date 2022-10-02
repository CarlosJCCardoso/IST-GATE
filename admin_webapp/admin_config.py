import json

admin_config = {"istID":["ist187161","ist190134"]}
myJSON = json.dumps(admin_config)

with open("admin_config.json", "w") as jsonfile:
    jsonfile.write(myJSON)
    print("Write successful")

