import yaml, sys

try:
    yaml_filepath = sys.argv[1]
except:
    raise Exception("yaml filepath/file.yaml not specified")

# Load YAML data from file
with open(yaml_filepath, 'r') as file:
    yaml_data = yaml.safe_load(file)

# Print the parsed YAML data
print("Parsed YAML data:")
print(yaml_data)

print(yaml_data['name'])
print(yaml_data['branch'])
print(yaml_data['environment'])

# TODO: Use arguments to talk to component db