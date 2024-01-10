# update_version.py

import sys

def update_version(version_file):
    with open(version_file, 'r') as file:
        current_version = file.read().strip()

    version_parts = list(map(int, current_version.split('.')))
    version_parts[-1] += 1  # Verhoog het laatste deel van het versienummer

    new_version = '.'.join(map(str, version_parts))

    with open(version_file, 'w') as file:
        file.write(new_version)

    return new_version

if __name__ == "__main__":
    version_file = sys.argv[1]
    new_version = update_version(version_file)
    print(f"::set-output name=new_version::{new_version}")
