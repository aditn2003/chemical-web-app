import pandas as pd
import math

R = 62.37     
T = 298        
fdep = 0.1     
Lsc = 1.34e-3 
RT = R * T

def compute_dermal_params(MW, LogKow, Pvap, Sw, nc, nh, nn, no, nring):
    Kow = 10 ** LogKow

    logkp = -2.8 + 0.66*LogKow - 0.0056*MW
    kp = 10 ** logkp 

    sumv = 16.5*nc + 1.98*nh + 5.69*nn + 5.48*no - 20.2*nring

    Dg = (1e-3 * 298**1.75 * math.sqrt((MW+29)/(MW*29))) / ((sumv**(1/3) + 20.1**(1/3))**2)

    kg = 3260 * (Dg**(2/3)) * math.sqrt(16.5/13.4)

    Ksc = 0.04*(Kow**0.81) + 0.359 + 4.057*(Kow**0.27)

    Csat = Ksc * Sw
    Mo = fdep * Lsc * 1000 * Csat

    D = (Lsc/3600) * 10**(-2.8 - 0.0056*MW) 

    chi = (kg * Pvap * MW) / (RT * kp * Sw) if (kp*Sw) != 0 else float("nan")

    return Mo, D, chi, kp, kg, Ksc, Csat

def main():
    df = pd.read_csv("backend/combined_chemicals.csv")

    kr_df = pd.read_csv("backend/kr_predictions_135.csv")[["Name", "Predicted_kr"]]

    df["Name_clean"] = df["Name"].str.strip().str.lower()
    kr_df["name_clean"] = kr_df["Name"].str.strip().str.lower()

    results = df.apply(
        lambda row: compute_dermal_params(
            row["MW"], row["logP"], row["vaporPressure"], row["solubility"],
            row["nc"], row["nh"], row["nn"], row["no"], row["nring"]
        ), axis=1
    )
    df[["Mo", "D", "chi", "kp", "kg", "Ksc", "Csat"]] = pd.DataFrame(results.tolist(), index=df.index)

    df = df.merge(kr_df[["name_clean", "Predicted_kr"]],
                  left_on="Name_clean", right_on="name_clean", how="left")

    df = df.rename(columns={"Predicted_kr": "Ksk"})

    df = df.drop(columns=["Name_clean", "name_clean"])

    aegl_cols = [col for col in df.columns if col.startswith("AEGL")]
    df = df.drop(columns=aegl_cols)

    df.to_csv("chemicals_with_mo_chi_d.csv", index=False)
    print("New CSV written: chemicals_with_mo_chi_d.csv")

if __name__ == "__main__":
    main()

