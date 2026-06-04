import requests
import pandas as pd
from datetime import datetime

# --- Configuration ---
# 392:UT:SNTL = Chalk Creek #1
# 393:UT:SNTL = Chalk Creek #2
STATIONS = "392:UT:SNTL,393:UT:SNTL"

# Elements we want to track:
# WTEQ = Snow Water Equivalent (water content of snow)
# SNWD = Snow Depth (height of snow)
# PREC = Precipitation Accumulation (total precip)
# TMAX, TMIN, TAVG = Air Temperatures
ELEMENTS = "WTEQ,SNWD,PREC,TMAX,TMIN,TAVG"

# Start Date (Water Year start is standard for snow data)
START_DATE = "2000-10-01" 

def fetch_weather_data():
    print("Connecting to USDA AWDB API...")
    
    # Endpoint from your documentation
    url = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data"
    
    # Parameters exactly as defined in the Swagger docs
    params = {
        "stationTriplets": STATIONS,
        "elements": ELEMENTS,
        "duration": "DAILY",
        "beginDate": START_DATE,
        "endDate": datetime.now().strftime("%Y-%m-%d"),
        "ordinal": "1" # Ensures we get the standard sensor
    }

    try:
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            print(response.text)
            return None

        data = response.json()
        
        # --- Processing the Nested JSON ---
        all_records = []

        # The API returns a list of Stations
        for station_item in data:
            station_id = station_item.get("stationTriplet")
            # Create a readable name
            station_name = "Chalk Creek #1" if "392" in station_id else "Chalk Creek #2"
            
            print(f"Processing data for {station_name}...")

            # Each station has a list of 'data' (one item per Element)
            for element_item in station_item.get("data", []):
                element_code = element_item["stationElement"]["elementCode"]
                
                # Each Element has a list of 'values' (Daily readings)
                for reading in element_item.get("values", []):
                    # We collect rows: Date, Station, Element, Value
                    if reading.get("value") is not None:
                        all_records.append({
                            "Date": reading["date"],
                            "Station_Id": station_id,
                            "Station_Name": station_name,
                            "Element": element_code,
                            "Value": reading["value"]
                        })

        # Convert to DataFrame
        df = pd.DataFrame(all_records)
        
        if df.empty:
            print("No data found.")
            return

        # --- Pivot for Power BI ---
        # Currently, data is "Long" (many rows per date). 
        # Power BI likes "Wide" (one row per date, many columns).
        print("Reshaping data for Power BI...")
        
        # We pivot on Date + Station
        df_pivot = df.pivot_table(
            index=["Date", "Station_Id", "Station_Name"], 
            columns="Element", 
            values="Value"
        ).reset_index()
        
        # Rename columns to be friendlier
        column_map = {
            "WTEQ": "Snow_Water_Equiv_in",
            "SNWD": "Snow_Depth_in",
            "PREC": "Precip_Accum_in",
            "TMAX": "Temp_Max_F",
            "TMIN": "Temp_Min_F",
            "TAVG": "Temp_Avg_F"
        }
        df_pivot.rename(columns=column_map, inplace=True)
        
        # Ensure Date format
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"])

        # --- Save ---
        output_file = "chalk_creek_weather.parquet"
        df_pivot.to_parquet(output_file, index=False)
        
        print("-" * 30)
        print(f"SUCCESS! Saved {len(df_pivot)} rows to {output_file}")
        print("Sample Data:")
        print(df_pivot.tail(3))

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    fetch_weather_data()
