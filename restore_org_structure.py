from pymongo import MongoClient
from app.settings import settings

def rebuild_org():
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    org_collection = db["org_structure"]

    clean_zones = {
        "SILIGURI ZONE": {
            "regions": {
                "DARJEELING REGION": {
                    "SILIGURI TOWN": {
                        "CCCs": [
                            {"name": "HAKIMPARA CCC", "code": "3412502"},
                            {"name": "MILANPALLY CCC", "code": "3412400"},
                            {"name": "NJP GATE BAZAR CCC", "code": "3412401"},
                            {"name": "POWER HOUSE CCC", "code": "3412503"},
                            {"name": "PRADHAN NAGAR CCC", "code": "3412504"},
                            {"name": "SILIGURI TOWN CCC", "code": "3412505"},
                            {"name": "SUBHASPALLY CCC", "code": "3412501"}
                        ],
                        "Sub-stations": [
                            "DABGRAM", "DESHBANDHUPARA", "HOUSING BOARD", "JHANKAR", "PURBA KARAIBARI SUB-STATION", 
                            "RABINDRANAGAR", "SALBARI", "SILIGURI", "SILVER OAKS", "SUBHASPALLY", 
                            "T.B HOSPITAL", "TINBATTI", "TINBATTI SUB-STATION", "UJANU"
                        ]
                    },
                    "SILIGURI SUBURBAN": {
                        "CCCs": [
                            {"name": "BAGDOGRA CCC", "code": "3415200"},
                            {"name": "BIDHANNAGAR CCC", "code": "3415201"},
                            {"name": "KHARIBARI CCC", "code": "3415103"},
                            {"name": "MATIGARA CCC", "code": "3415400"},
                            {"name": "NAXALBARI CCC", "code": "3415101"},
                            {"name": "PHANSIDEWA CCC", "code": "3415102"},
                            {"name": "SHIVMANDIR CCC", "code": "3415600"}
                        ],
                        "Sub-stations": [
                            "BAGDOGRA", "BIDHANNAGAR", "EMBEE DELIGHT", "GHOSHPUKUR", "HATIGHISHA", 
                            "KAWAKHALI", "KHAPRAIL", "KHARIBARI", "NBU GSS", "SHANTINIKETAN", 
                            "TCF 33/11 KV", "UPWAN", "UTSODHAARA", "UTTORA", "VASTU BIHAR"
                        ]
                    },
                    "KURSEONG": {
                        "CCCs": [
                            {"name": "KURSEONG CCC", "code": "3413202"},
                            {"name": "MIRIK CCC", "code": "3413201"},
                            {"name": "SONADA CCC", "code": "3413101"}
                        ],
                        "Sub-stations": [
                            "FAZI POWER HOUSE", "JOGIGHAT", "MIRIK", "PANKHABARI", "SONADA"
                        ]
                    },
                    "DARJEELING": {
                        "CCCs": [
                            {"name": "DARJEELING CCC", "code": "3414300"},
                            {"name": "BIJANBARI CCC", "code": "3414201"},
                            {"name": "LODHOMA CCC", "code": "3414204"},
                            {"name": "SUKHIAPOKHRI CCC", "code": "3414101"},
                            {"name": "TAKDAH CCC", "code": "3414102"}
                        ],
                        "Sub-stations": [
                            "BIJANBARI", "HAPPY VALLEY", "LEBONG PH", "LODHAMA", "NEW GHOOM", 
                            "OLD GHOOM", "POKHRIABONG", "RAMMAM GSS", "SINGAMARI", "TAKDAH"
                        ]
                    }
                },
                "JALPAIGURI REGION": {
                    "JALPAIGURI": {
                        "CCCs": [
                            {"name": "BELAKOBA CCC", "code": "3422102"},
                            {"name": "BHOTPATTY CCC", "code": "3422206"},
                            {"name": "DHUPGURI CCC", "code": "3422301"},
                            {"name": "FULBARIHAT CCC", "code": "3422108"},
                            {"name": "MAYNAGURI CCC", "code": "3422201"},
                            {"name": "NAYABASTI PANDAPARA CCC", "code": "3422401"},
                            {"name": "UKILPARA MASKALAIBARI CCC", "code": "3422402"}
                        ],
                        "Sub-stations": [
                            "AMBARI-FALAKATA 33/11KV S/S", "BERUBARI", "BHOTPATTY 33/11 KV", "DHUPGURI", "FATAPUKUR", 
                            "FULBARI 33/11KV S/S", "FULBARI INDUSTRIAL PARK", "HUSLUDANGA", "JALPAIGURI TOWN 33/11KV SUBSTATION", "MOHITNAGAR", 
                            "MOYNAGURI GSS", "NEW JALPAIGURI GSS", "PAHARPUR", "PANDAPARA", "RADHABARI", "RANINAGAR"
                        ]
                    },
                    "MAL": {
                        "CCCs": [
                            {"name": "BANARHAT CCC", "code": "3427106"},
                            {"name": "GAIRKATA CCC", "code": "3427201"},
                            {"name": "JHALONG PAREN CCC", "code": "3427104"},
                            {"name": "KRANTI CCC", "code": "3427108"},
                            {"name": "MAL CCC", "code": "3427101"},
                            {"name": "MATELLI CCC", "code": "3427103"},
                            {"name": "NAGRAKATA CCC", "code": "3427105"},
                            {"name": "OODLABARI CCC", "code": "3427102"}
                        ],
                        "Sub-stations": [
                            "BANARHAT GSS", "CHALSA GSS", "GARUBATHAN", "GAYERKATA", "GAZOLDOBA", 
                            "JALDHAKA", "JALDHAKA STAGE-1", "LATAGURI", "MALBAZAR", "NAGRAKATA GSS", "ODLABARI GSS"
                        ]
                    }
                },
                "ALIPURDUAR REGION": {
                    "ALIPURDUAR": {
                        "CCCs": [
                            {"name": "ALIPURDUAR NEW TOWN CCC", "code": "3453400"},
                            {"name": "ALIPURDUAR PURAN BAZAR CCC", "code": "3453101"},
                            {"name": "BIRPARA CCC", "code": "3453202"},
                            {"name": "FALAKATA CCC", "code": "3453203"},
                            {"name": "JAIGAON CCC", "code": "3453106"},
                            {"name": "KALCHINI CCC", "code": "3453102"},
                            {"name": "KAMAKHYAGURI CCC", "code": "3453103"},
                            {"name": "MADARIHAT CCC", "code": "3453201"},
                            {"name": "MEJBIL CCC", "code": "3453206"},
                            {"name": "SAMUKTALA CCC", "code": "3453107"}
                        ],
                        "Sub-stations": [
                            "33/11 KV ALIPURDUAR GIS", "ALIPURDUAR", "ALIPURDUAR GSS", "BAROBHISA", "BIRPARA GSS", 
                            "DAMANPUR", "FALAKATA", "GARGANDA", "HAMILTONGANJ GSS", "HASHIMARA GSS", 
                            "JAIGAON", "JASODANGA", "KAMAKHYAGURI GSS", "KARTIKA", "KUMARGRAM", "MADARIHAT", "SONAPUR GIS"
                        ]
                    }
                },
                "COOCHBEHAR REGION": {
                    "COOCHBEHAR": {
                        "CCCs": [
                            {"name": "BOXIRHAT CCC", "code": "3444506"},
                            {"name": "COOCHBEHAR CCC", "code": "3444300"},
                            {"name": "KHAGRABARI CCC", "code": "3444301"},
                            {"name": "NEWTOWN CCC", "code": "3444302"},
                            {"name": "PUNDIBARI CCC", "code": "3444303"},
                            {"name": "TUFANGANJ CCC", "code": "3444503"}
                        ],
                        "Sub-stations": [
                            "BANESWAR", "BAXIRHAT", "CHAKCHAKA", "CHILAKHANA SUBSTATION", "COOCHBEHAR (KHAGRABARI)", 
                            "COOCHBEHAR POWER HOUSE", "GHUGUMARI", "PUNDIBARI", "RUSTOM(APDCL)", "TUFANGANJ", 
                            "VIRTUAL_KHAMARPARA", "VIRTUAL_NAYAPARA"
                        ]
                    },
                    "MATHABHANGA": {
                        "CCCs": [
                            {"name": "CHANGRABANDHA CCC", "code": "3445106"},
                            {"name": "DOLONGMORE CCC", "code": "3445104"},
                            {"name": "HALDIBARI CCC", "code": "3445105"},
                            {"name": "MATHABHANGA CCC", "code": "3445101"},
                            {"name": "SITALKUCHI CCC", "code": "3445102"}
                        ],
                        "Sub-stations": [
                            "AKRARHAT", "BHOGRAMGURI(JAMALDA)", "CHANGRABANDHA", "GHOKHSADANGA", 
                            "HALDIBARI", "MATHABHANGA", "MEKLIGANJ", "SITALKUCHI"
                        ]
                    },
                    "DINHATA": {
                        "CCCs": [
                            {"name": "DEWANHAT CCC", "code": "3446105"},
                            {"name": "DINHATA CCC", "code": "3446101"},
                            {"name": "OKRABARI CCC", "code": "3446102"},
                            {"name": "SAHEBGANJ CCC", "code": "3446103"},
                            {"name": "SITAI CCC", "code": "3446104"}
                        ],
                        "Sub-stations": [
                            "BALARAMPUR", "BAMANHAT", "DEWANHAT", "DINHATA", "NAYARHAT", "PETLA", "SITAI"
                        ]
                    }
                },
                "KALIMPONG REGION": {
                    "KALIMPONG": {
                        "CCCs": [
                            {"name": "KALIMPONG CCC", "code": "3471101"},
                            {"name": "MONGPU CCC", "code": "3471103"},
                            {"name": "PEDONG CCC", "code": "3471104"},
                            {"name": "SINJEE CCC", "code": "3471105"},
                            {"name": "TEESTA BAZAR CCC", "code": "3471102"}
                        ],
                        "Sub-stations": [
                            "KALIMPONG(HILL VIEW) GSS", "PALA", "PEDONG"
                        ]
                    }
                }
            }
        },
        "MALDA ZONE": {
            "regions": {
                "MALDA REGION": {
                    "MALDA": {
                        "CCCs": [
                            {"name": "BAISHNABNAGAR CCC", "code": "6611103"},
                            {"name": "FULBARI CCC", "code": "6611108"},
                            {"name": "GOLAPGANJ CCC", "code": "6611102"},
                            {"name": "KALIACHAK CCC", "code": "6611104"},
                            {"name": "MANIKCHAK CCC", "code": "6611101"},
                            {"name": "MOKDUMPUR CCC", "code": "6611109"},
                            {"name": "MOTHABARI CCC", "code": "6611105"},
                            {"name": "RATHBARI CCC", "code": "6611107"},
                            {"name": "SUJAPUR CCC", "code": "6611106"}
                        ],
                        "Sub-stations": [
                            "BAISHNABNAGAR", "ENGLISHBAZAR", "GOLAPGANJ", "KALIACHAK", "KPS", "MALDA GSS", 
                            "MANIKCHAK", "MILKY", "MOTHABARI", "RABINDRA BHAVAN", "SUJAPUR"
                        ]
                    },
                    "CHANCHAL": {
                        "CCCs": [
                            {"name": "BHALUKA CCC", "code": "6612101"},
                            {"name": "CHANCHAL CCC", "code": "6612104"},
                            {"name": "HARISHCHANDRAPUR CCC", "code": "6612106"},
                            {"name": "KUSHIDA CCC", "code": "6612107"},
                            {"name": "MALATIPUR CCC", "code": "6612105"},
                            {"name": "PARANPUR CCC", "code": "6612103"},
                            {"name": "SAMSI CCC", "code": "6612102"}
                        ],
                        "Sub-stations": [
                            "ASHAPUR", "BHAKURIA VIRTUAL SS", "BHALUKA", "CHANCHAL", "CHATRAK", "HARISHCHANDRAPUR", 
                            "MAGURA TEMPORARY SUB STATION", "PUKURIA", "RATUA", "SAMSI GSS", "SHIBNAGAR", "TULSHIHATA TEMPORARY SUBSTATION"
                        ]
                    },
                    "GAZOLE": {
                        "CCCs": [
                            {"name": "AIHO CCC", "code": "6613102"},
                            {"name": "BAMONGOLA CCC", "code": "6613104"},
                            {"name": "GAZOL CCC", "code": "6613101"},
                            {"name": "OLD MALDA CCC", "code": "6613105"},
                            {"name": "PANDUA", "code": "6613103"}
                        ],
                        "Sub-stations": [
                            "BALIA", "BAMANGOLA", "DEOTALA 33/11 KV", "GAZOL", "GAZOLE 220 KV GSS", "HABIBPUR", 
                            "MANGALBARI GIS", "MOBARAKPUR", "NALAGOLA", "NARAYANPUR(MALDA)", "RANIPUR O/D", "RIDDHI SIDDHI"
                        ]
                    }
                },
                "U/DINAJPUR REGION": {
                    "RAIGANJ": {
                        "CCCs": [
                            {"name": "BIRNAGAR CCC", "code": "6621105"},
                            {"name": "HEMTABAD CCC", "code": "6621102"},
                            {"name": "ITAHAR CCC", "code": "6621101"},
                            {"name": "KALIYAGANJ CCC", "code": "6621103"},
                            {"name": "KARANDIGHI CCC", "code": "6621106"},
                            {"name": "RAIGANJ CCC", "code": "6621104"}
                        ],
                        "Sub-stations": [
                            "BANGAR", "BIKORE", "DURGAPUR", "HEMTABAD", "ITAHAR", "KALIAGANJ", 
                            "KASBA", "LAXMANIA", "MALON", "RAIGANJ GSS", "RAIGANJ OLD", "TUNGIDIGHI 33/11 KV SUBSTATION"
                        ]
                    },
                    "ISLAMPUR": {
                        "CCCs": [
                            {"name": "CHOPRA CCC", "code": "6622102"},
                            {"name": "DALKHOLA CCC", "code": "6622103"},
                            {"name": "GOALPOKHER CCC", "code": "6622104"},
                            {"name": "ISLAMPUR CCC", "code": "6622101"},
                            {"name": "KANKI CCC", "code": "6622105"}
                        ],
                        "Sub-stations": [
                            "BHOLAGACH", "CHOPRA", "CHOPRAJHAR", "DALKHOLA GSS", "ISLAMPUR", 
                            "KAHATA", "KANKI SUBSTATION", "LODHAN", "PANJIPARA", "SONAPUR", "SRIKRISHNAPUR"
                        ]
                    }
                },
                "D/DINAJPUR REGION": {
                    "BALURGHAT": {
                        "CCCs": [
                            {"name": "BALURGHAT CCC", "code": "6631101"},
                            {"name": "HILI CCC", "code": "6631104"},
                            {"name": "KUMARGANJ CCC", "code": "6631103"},
                            {"name": "PATIRAM CCC", "code": "6631105"},
                            {"name": "TAPAN CCC", "code": "6631102"}
                        ],
                        "Sub-stations": [
                            "AMRAIL", "BALURGHAT(MAHINAGAR) GSS", "BARO RAGHUNATHPUR", "LASKARHAT", 
                            "MAHIPUR", "PATIRAM", "RAMPUR", "SALAS", "TRIMOHINI"
                        ]
                    },
                    "BUNIADPUR": {
                        "CCCs": [
                            {"name": "BUNIADPUR CCC", "code": "6632101"},
                            {"name": "GANGARAMPUR CCC", "code": "6632104"},
                            {"name": "HARIRAMPUR CCC", "code": "6632103"},
                            {"name": "KUSMANDI CCC", "code": "6632102"}
                        ],
                        "Sub-stations": [
                            "BUNIADPUR", "GANGARAMPUR GSS", "HARIRAMPUR", "KUSHMUNDI", 
                            "MALIGAON 33/11KV GIS", "PRANSAGAR", "THANGAPARA 33/11 KV SUB-STATION"
                        ]
                    }
                }
            }
        }
    }

    org_collection.delete_many({})
    org_collection.insert_one({"zones": clean_zones})
    
    print("✅ Successfully rebuilt org_structure with EXACT Sub-stations for Siliguri & Malda!")
    print("👉 All divisions and their respective sub-stations are now mapped.")

if __name__ == "__main__":
    rebuild_org()