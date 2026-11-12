from pymongo import MongoClient
from app.settings import settings

def migrate_cccs():
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    org_collection = db["org_structure"]
    
    # 1. THE COMPLETE MASTER MAP (All Zones & Codes)
    ccc_map = {
        "HAKIMPARA": "3412502", "MILANPALLY": "3412400", "NJP GATE BAZAR": "3412401",
        "POWER HOUSE": "3412503", "PRADHAN NAGAR": "3412504", "SILIGURI TOWN": "3412505",
        "SUBHASPALLY": "3412501", "KURSEONG": "3413202", "MIRIK": "3413201",
        "SONADA": "3413101", "BIJANBARI": "3414201", "DARJEELING": "3414300",
        "LODHOMA": "3414204", "SUKHIAPOKHRI": "3414101", "TAKDAH": "3414102",
        "BAGDOGRA": "3415200", "BIDHANNAGAR": "3415201", "KHARIBARI": "3415103",
        "MATIGARA": "3415400", "NAXALBARI": "3415101", "PHANSIDEWA": "3415102",
        "SHIVMANDIR": "3415600", "BELAKOBA": "3422102", "BHOTPATTY": "3422206",
        "DHUPGURI": "3422301", "FULBARIHAT": "3422108", "MAYNAGURI": "3422201",
        "NAYABASTI PANDAPARA": "3422401", "UKILPARA MASKALAIBARI": "3422402",
        "BANARHAT": "3427106", "GAIRKATA": "3427201", "JHALONG PAREN": "3427104",
        "KRANTI": "3427108", "MAL": "3427101", "MATELLI": "3427103",
        "NAGRAKATA": "3427105", "OODLABARI": "3427102", "BOXIRHAT": "3444506",
        "COOCHBEHAR": "3444300", "KHAGRABARI": "3444301", "NEWTOWN": "3444302",
        "PUNDIBARI": "3444303", "TUFANGANJ": "3444503", "CHANGRABANDHA": "3445106",
        "DOLONGMORE": "3445104", "HALDIBARI": "3445105", "MATHABHANGA": "3445101",
        "SITALKUCHI": "3445102", "DEWANHAT": "3446105", "DINHATA": "3446101",
        "OKRABARI": "3446102", "SAHEBGANJ": "3446103", "SITAI": "3446104",
        "ALIPURDUAR NEW TOWN": "3453400", "ALIPURDUAR PURAN BAZAR": "3453101",
        "BIRPARA": "3453202", "FALAKATA": "3453203", "JAIGAON": "3453106",
        "KALCHINI": "3453102", "KAMAKHYAGURI": "3453103", "MADARIHAT": "3453201",
        "MEJBIL": "3453206", "SAMUKTALA": "3453107", "KALIMPONG": "3471101",
        "MONGPU": "3471103", "PEDONG": "3471104", "SINJEE": "3471105",
        "TEESTA BAZAR": "3471102", 
        
        "BAISHNABNAGAR": "6611103", "FULBARI": "6611108", "GOLAPGANJ": "6611102", 
        "KALIACHAK": "6611104", "MANIKCHAK": "6611101", "MOKDUMPUR": "6611109", 
        "MOTHABARI": "6611105", "RATHBARI": "6611107", "SUJAPUR": "6611106", 
        "BHALUKA": "6612101", "CHANCHAL": "6612104", "HARISHCHANDRAPUR": "6612106", 
        "KUSHIDA": "6612107", "MALATIPUR": "6612105", "PARANPUR": "6612103", 
        "SAMSI": "6612102", "AIHO": "6613102", "BAMONGOLA": "6613104", 
        "GAZOL": "6613101", "OLD MALDA": "6613105", "PANDUA": "6613103", 
        "BIRNAGAR": "6621105", "HEMTABAD": "6621102", "ITAHAR": "6621101", 
        "KALIYAGANJ": "6621103", "KARANDIGHI": "6621106", "RAIGANJ": "6621104", 
        "CHOPRA": "6622102", "DALKHOLA": "6622103", "GOALPOKHER": "6622104", 
        "ISLAMPUR": "6622101", "KANKI": "6622105", "BALURGHAT": "6631101", 
        "HILI": "6631104", "KUMARGANJ": "6631103", "PATIRAM": "6631105", 
        "TAPAN": "6631102", "BUNIADPUR": "6632101", "GANGARAMPUR": "6632104", 
        "HARIRAMPUR": "6632103", "KUSMANDI": "6632102"
    }

    # 2. ALIASES (Fixes spelling differences between org_structure and your CSV)
    aliases = {
        "SUBHASPALLI": "SUBHASPALLY",
        "MILANPALLI": "MILANPALLY",
        "SHIBMANDIR": "SHIVMANDIR",
        "BIJONBARI": "BIJANBARI",
        "LODHAMA": "LODHOMA",
        "SUKHIAPOKRI": "SUKHIAPOKHRI",
        "TEESTABAZAR": "TEESTA BAZAR",
        "BELACOBA": "BELAKOBA",
        "MOYNAGURI": "MAYNAGURI",
        "NAGRA KATA": "NAGRAKATA",
        "MATELI": "MATELLI",
        "JHALONG PEREN": "JHALONG PAREN",
        "TOOFANGANJ": "TUFANGANJ",
        "DALONGMORE": "DOLONGMORE",
        "CHANGRA BANDHA": "CHANGRABANDHA",
        "MOKDAMPUR": "MOKDUMPUR",
        "KALIACAK": "KALIACHAK",
        "BAISNABNAGAR": "BAISHNABNAGAR",
        "H.C. PUR": "HARISHCHANDRAPUR",
        "BAMANGOLA": "BAMONGOLA",
        "KALIAGANJ": "KALIYAGANJ",
        "GOALPOKHAR": "GOALPOKHER",
        "KUMARGUNJ": "KUMARGANJ",
        "KUSHMUNDI": "KUSMANDI",
        # Fixes for the extra names you listed
        "UM SECTOR": "6615200", 
        "NBPP SECTOR": "6615201",
        "MATHURAPUR": "6611107" # Assuming Mathurapur matches Rathbari area code
    }

    org_doc = org_collection.find_one()
    if not org_doc:
        print("❌ No org_structure document found!")
        return

    zones = org_doc.get("zones", {})
    updated_count = 0
    missing_list = []

    for zone_name, zone_data in zones.items():
        for reg_name, reg_data in zone_data.get("regions", {}).items():
            for div_name, div_data in reg_data.items():
                ccc_list = div_data.get("CCCs", [])
                new_ccc_list = []
                
                for ccc in ccc_list:
                    # Get the current name
                    original_name = ccc.get("name") if isinstance(ccc, dict) else str(ccc)
                    
                    # Clean it: remove "CCC", strip spaces, uppercase
                    clean_name = original_name.upper().replace("CCC", "").strip()
                    
                    # Apply the alias if it exists
                    if clean_name in aliases:
                        clean_name = aliases[clean_name]
                    
                    matched_code = ""
                    # 1. Exact match on cleaned name
                    if clean_name in ccc_map:
                        matched_code = ccc_map[clean_name]
                    else:
                        # 2. Partial match (if org has extra words)
                        for map_name, code in ccc_map.items():
                            if map_name in clean_name or clean_name in map_name:
                                matched_code = code
                                break
                    
                    if matched_code:
                        new_ccc_list.append({"name": original_name, "code": matched_code})
                        updated_count += 1
                    else:
                        new_ccc_list.append({"name": original_name, "code": ""})
                        if original_name not in missing_list:
                            missing_list.append(original_name)
                
                div_data["CCCs"] = new_ccc_list

    # 3. Save to DB
    org_collection.update_one({"_id": org_doc["_id"]}, {"$set": {"zones": zones}})
    
    print(f"✅ Success! Updated {updated_count} CCCs with codes.")
    if missing_list:
        print(f"⚠️ Could not find codes for: {', '.join(missing_list)}")
    else:
        print("🎉 100% Match! All CCCs were successfully updated.")

if __name__ == "__main__":
    migrate_cccs()