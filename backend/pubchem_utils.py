import re
import pubchempy as pcp
import pandas as pd
import requests
from rdkit import Chem

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
CLASS_PATTERNS = {
    "Nerve agent": ["COP(=O)(F)OC", "P(=O)(F)", "P(=O)(OC)(F)"],
    "Blister agent": ["[Cl][CH2][CH2]S", "S=C=N"],
    "Nitroaromatic": ["c1ccc(cc1)[N+](=O)[O-]"],
    "Aromatic hydrocarbon": ["c1ccccc1"],
    "Alcohol": ["[CX4][OH]"],
    "Ketone": ["C(=O)[CX4]"],
}

def infer_class_from_smarts(mol):
    for class_name, smarts_list in CLASS_PATTERNS.items():
        for smarts in smarts_list:
            if mol.HasSubstructMatch(Chem.MolFromSmarts(smarts)):
                return class_name
    return "Other"

def extract_cas_from_synonyms(syns):
    if not syns:
        return None
    for s in syns:
        if CAS_RE.match(s):
            return s
    return None

def get_smiles_from_pubchem(name: str) -> str | None:
    name_variants = [name, name.lower(), name.capitalize(), name.upper()]

    for variant in name_variants:
        try:
            compounds = pcp.get_compounds(variant, 'name')
            if compounds and compounds[0].canonical_smiles:
                return compounds[0].canonical_smiles
        except Exception:
            continue

        try:
            cids = pcp.get_cids(variant, 'name')
            if cids:
                compound = pcp.Compound.from_cid(cids[0])
                if compound.canonical_smiles:
                    return compound.canonical_smiles
        except Exception:
            continue

    # Synonym search
    try:
        cids = pcp.get_cids(name, 'synonym')
        if cids:
            compound = pcp.Compound.from_cid(cids[0])
            if compound.canonical_smiles:
                return compound.canonical_smiles
    except Exception:
        pass

    # Final fallback to REST
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/CanonicalSMILES,ConnectivitySMILES/JSON"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            properties = data.get("PropertyTable", {}).get("Properties", [])
            if properties:
                if "CanonicalSMILES" in properties[0]:
                    return properties[0]["CanonicalSMILES"]
                elif "ConnectivitySMILES" in properties[0]:
                    return properties[0]["ConnectivitySMILES"]
    except Exception as e:
        print(f"[PubChem error] Failed REST fallback for {name}: {e}")


    print(f"[PubChem error] Could not fetch SMILES for {name}")
    return None

def safe_mol_from_smiles(smiles, Name="unknown"):
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        Chem.SanitizeMol(mol)
        return mol
    except:
        return None

def _pubchem_compound_by_name_or_cas(name):
    try:
        res = pcp.get_compounds(name, "name")
        if res:
            return res[0]
    except: pass

    try:
        if CAS_RE.match(name):
            res = pcp.get_compounds(name, "registry_id")
            if res:
                return res[0]
    except: pass

    try:
        subs = pcp.get_substances(name)
        for s in subs or []:
            if getattr(s, "cid", None):
                return pcp.Compound(s.cid)
    except: pass

    return None

def build_compound(name, compound_db, safe_convert_func):
    row = compound_db[compound_db["Name"].str.lower() == name.lower()]
    if not row.empty:
        compound = row.iloc[0].to_dict()
        compound = {k: v for k, v in compound.items() if pd.notnull(v)}
        if "logKow" not in compound and "logP" in compound:
            compound["logKow"] = compound["logP"]
        return safe_convert_func(compound)

    c = _pubchem_compound_by_name_or_cas(name)
    if not c: return None

    smiles = get_smiles_from_pubchem(name)
    cas = extract_cas_from_synonyms(getattr(c, "synonyms", []))
    xlogp = getattr(c, "xlogp", None)
    mw = getattr(c, "molecular_weight", None)
    formula = getattr(c, "molecular_formula", None)

    mol = safe_mol_from_smiles(smiles, name) if smiles else None
    inferred_class = infer_class_from_smarts(mol) if mol else "Other"

    print(f"[DEBUG] Compound: {name}")
    print(f"[DEBUG] SMILES: {smiles}")
    print(f"[DEBUG] Inferred Class: {inferred_class}")
    print(f"[DEBUG] MW: {mw} | logP: {xlogp}")

    return safe_convert_func({
        "Name": name,
        "CAS": cas,
        "MW": mw,
        "logP": xlogp,
        "logKow": xlogp,
        "formula": formula,
        "class": inferred_class or "Other",
        "SMILES": smiles,
        "henryConstant": None,
        "vaporPressure": None,
        "solubility": None
    })

def hasAeglSupport(compound):
    has_any = any(k.startswith("AEGL") for k in compound.keys())
    required = ["MW", "logKow", "henryConstant", "vaporPressure", "solubility"]
    missing = [k for k in required if compound.get(k) in [None, "", "undefined"]]
    if not has_any:
        return False, "No AEGL values found."
    if missing:
        return False, f"Missing parameters: {', '.join(missing)}"
    return True, ""
