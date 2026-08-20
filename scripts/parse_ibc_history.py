"""
Parse historico-ibc.md y guarda en BD (ibc_index table).
Uso: python scripts/parse_ibc_history.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
from datetime import datetime, timezone
from src.db.session import session_scope
from src.db.models import IBCIndexORM
from sqlalchemy import select

def parse_number_es(text: str) -> float:
    """Parsea número formato español (3.368,39 -> 3368.39)."""
    if not text or text.strip() in ("-", "0,00", "0.00"):
        return 0.0
    # Replace dots (thousands) and comma (decimal)
    cleaned = text.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def parse_date_es(text: str) -> datetime:
    """Parsea fecha DD/MM/YYYY -> datetime UTC."""
    day, month, year = map(int, text.strip().split("/"))
    return datetime(year, month, day, tzinfo=timezone.utc)

def main():
    filepath = r"C:\Users\DeadW\dev\economia-venezuela\data\reports\historico-ibc.md"
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split by month sections
    # Pattern: "Período:\nDesde DD/MM/YYYY hasta DD/MM/YYYY\n\nFecha\tApertura\tCierre..."
    sections = re.split(r'Per[ií]odo:', content)[1:]  # Skip first empty
    
    all_records = []
    
    for section in sections:
        lines = section.strip().split("\n")
        if len(lines) < 3:
            continue
            
        # Find data lines (tab-separated with date at start)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Check if line starts with date pattern DD/MM/YYYY
            if re.match(r"^\d{2}/\d{2}/\d{4}\t", line):
                parts = line.split("\t")
                if len(parts) >= 3:
                    date_str = parts[0]
                    close_str = parts[2]  # Cierre column
                    change_pct_str = parts[3] if len(parts) > 3 else "0"
                    change_str = parts[4] if len(parts) > 4 else "0"
                    
                    date = parse_date_es(date_str)
                    close = parse_number_es(close_str)
                    change_pct = parse_number_es(change_pct_str.replace("%", "").replace("+", ""))
                    change = parse_number_es(change_str.replace("+", ""))
                    
                    if close > 0:
                        all_records.append({
                            "date": date,
                            "value": close,
                            "change": change,
                            "change_pct": change_pct,
                        })
    
    print(f"Parsed {len(all_records)} IBC records")
    
    # Sort by date
    all_records.sort(key=lambda x: x["date"])
    
    # Show first and last
    if all_records:
        print(f"First: {all_records[0]['date'].date()} = {all_records[0]['value']}")
        print(f"Last:  {all_records[-1]['date'].date()} = {all_records[-1]['value']}")
    
    # Save to DB
    with session_scope() as session:
        saved = 0
        updated = 0
        for record in all_records:
            existing = session.execute(
                select(IBCIndexORM).where(IBCIndexORM.date == record["date"])
            ).scalar_one_or_none()
            
            if existing:
                existing.value = record["value"]
                existing.change = record["change"]
                existing.change_pct = record["change_pct"]
                updated += 1
            else:
                session.add(IBCIndexORM(
                    date=record["date"],
                    value=record["value"],
                    change=record["change"],
                    change_pct=record["change_pct"],
                ))
                saved += 1
        
        session.commit()
        print(f"Saved: {saved}, Updated: {updated}")

if __name__ == "__main__":
    main()