from datetime import datetime

def log_action(action: str):
    print(f"[AUDIT] {action} | {datetime.utcnow()}")
