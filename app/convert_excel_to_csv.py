import pandas as pd
import re

# Define the mapping between Excel names and your Org Structure names
ALIAS_MAP = {
    "NBU 132/33/11 KV": "NBU GSS",
    "Khaprail 33/11 KV": "KHAPRAIL",
    "Hatighisha 33/11 KV": "HATIGHISHA",
    "Kharibari 33/11 KV": "KHARIBARI",
    "Bagdogra 33/11kv": "BAGDOGRA",
    "Bagdogra 33/11 KV": "BAGDOGRA",
    "Bidhannagar 33/11 KV": "BIDHANNAGAR",
    "Ghoshpukur 33/11 KV": "GHOSHPUKUR",
    "TCF 33/11 KV": "TCF 33/11 KV",
    "Kawakhali 33/11kv": "KAWAKHALI",
    "Kawakhali 33/11 KV": "KAWAKHALI",
    "Shantiniketan 33/11 KV": "SHANTINIKETAN",
    "Uttora 33/11 KV": "UTTORA",
    "Vastu Bihar 33/11 KV": "VASTU BIHAR",
    "Embee Delight 33/11 KV": "EMBEE DELIGHT",
    "Upwan 33/11 KV": "UPWAN",
    "Upwan 33/11KV": "UPWAN"
}

def time_to_decimal(time_str):
    if pd.isna(time_str) or str(time_str) == '00:00:00':
        return 0.0
    match = re.match(r'(\d+):(\d+):(\d+)', str(time_str))
    if match:
        h, m, s = map(int, match.groups())
        return round(h + m/60 + s/3600, 2)
    return 0.0

def process_excel():
    file_path = "Interruption SSD OCT 2026.xlsx"
    
    # Read both sheets
    df_33 = pd.read_excel(file_path, sheet_name="33 KV", skiprows=5)
    df_11 = pd.read_excel(file_path, sheet_name="11 KV", skiprows=5)

    all_data = []

    for df, voltage in [(df_33, "33 KV"), (df_11, "11 KV")]:
        # Keep only rows that have a feeder name
        df = df[df['Name of the feeder'].notna()]
        
        # Fill down the merged Substation names
        df['Name of the S/Stn'] = df['Name of the S/Stn'].ffill()

        for index, row in df.iterrows():
            excel_sub = str(row['Name of the S/Stn']).strip()
            
            # Match to Org Structure name
            org_sub = ALIAS_MAP.get(excel_sub, excel_sub)

            # Note: Change 'Outages' and 'Nos.' to the EXACT column names from your Excel if they differ
            # For example, if the column is named 'Outages (H:M)', use that.
            outage_val = row.get('Outages', 0) 
            trips_val = row.get('Nos.', 0)
            avail_val = row.get('Availability of Power', 0)

            all_data.append({
                "zone": "SILIGURI ZONE",
                "region": "DARJEELING REGION",
                "division": "SILIGURI SUB- URBAN DIVISION",
                "substation": org_sub,
                "feeder_name": str(row['Name of the feeder']).strip(),
                "daily_outage": time_to_decimal(outage_val),
                "monthly_outage": time_to_decimal(outage_val),
                "trips": trips_val,
                "yearly_outage": 0,
                "availability": avail_val,
                "voltage": voltage
            })

    final_df = pd.DataFrame(all_data)
    final_df.to_csv("dashboard_upload.csv", index=False)
    print("✅ CSV Created Successfully: dashboard_upload.csv")

if __name__ == "__main__":
    process_excel()