import pandas as pd

compound_db = pd.read_csv("Database/combined_chemicals.csv")

aeglCols = [col for col in compound_db.columns if "AEGL" in col or "henryConstant" in col]
for col in aeglCols:
    compound_db[col] = pd.to_numeric(compound_db[col], errors="coerce")

compoundList = [row.to_dict() for _, row in compound_db.iterrows()]
nameToCompound = {c["Name"]: c for c in compoundList}
