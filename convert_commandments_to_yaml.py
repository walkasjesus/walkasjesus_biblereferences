import csv
import yaml
import os
from collections import defaultdict

# Paths to the input CSV file and output YAML file
csv_file_path = "commandments.csv"
yaml_file_path = "commandments.yaml"

# Function to convert CSV to YAML
def convert_csv_to_yaml(csv_file_path, yaml_file_path):
    data = defaultdict(lambda: defaultdict(list))
    with open(csv_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';')
        for row in reader:
            step = row['step']
            bible_ref_info = {
                "bible_ref": row["bible_ref"],
                "bible_ref_positive_negative": row["bible_ref_positive_negative"],
                "bible_ref_ot_nr": row["bible_ref_ot_nr"],
                "bible_ref_ot_rambam_id": row["bible_ref_ot_rambam_id"],
                "bible_ref_ot_rambam_title": row["bible_ref_ot_rambam_title"],
                "bible_ref_author": row["bible_ref_author"],
                "bible_ref_type": row["bible_ref_type"]
            }
            for key, value in row.items():
                if key not in ['step', 'questions', 'quote', 'quote_source', 'bible_ref', 'bible_ref_positive_negative', 'bible_ref_ot_nr', 'bible_ref_ot_rambam_id', 'bible_ref_ot_rambam_title', 'bible_ref_author', 'bible_ref_type']:
                    if value:
                        data[step][key].append(value)
            data[step]["bible_refs"].append(bible_ref_info)

    # Convert defaultdict to regular dict and handle single items
    formatted_data = []
    for step, attributes in data.items():
        item = {'step': step}
        for key, values in attributes.items():
            item[key] = values if len(values) > 1 else values[0]
        formatted_data.append(item)

    # Save the data to a YAML file
    with open(yaml_file_path, "w") as yaml_file:
        yaml.dump(formatted_data, yaml_file, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"YAML data has been written to {yaml_file_path}")

# Run the conversion function
convert_csv_to_yaml(csv_file_path, yaml_file_path)