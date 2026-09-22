import subprocess
import random

def create_db_with_n_records():
    # Generate n insert commands
    n = 100
    commands = [f"insert {i} user{i} person{i}@example.com" for i in range(1, n)]
    random.shuffle(commands)
    
    # Run a select command to output the records, then exit
    commands.extend(["select", ".exit"])
    
    # Format the input data with newlines
    input_data = "\n".join(commands) + "\n"
    
    # Execute the database script and target mydb.db
    result = subprocess.run(
        ["python3", "./main.py", "mydb.db"],
        input=input_data,
        text=True,
        capture_output=True
    )
    
    # Output the results to the console
    for line in result.stdout.split("\n"):
        print(line)

    if result.returncode != 0 or result.stderr:
        print(result.stderr)

if __name__ == '__main__':
    create_db_with_n_records()
