import sys
import os

def main():
    log_path = r"C:\Users\dongl\.gemini\antigravity-ide\brain\86cf19b6-7452-476f-87d1-f0cda5476064\.system_generated\tasks\task-79.log"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print("Log file not found at:", log_path)

if __name__ == "__main__":
    main()
