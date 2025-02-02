import pandas as pd
import numpy as np
import plotly.graph_objects as go
from tkinter import Tk
from tkinter.filedialog import askopenfilename

# Helper function to load metadata and telemetry
def load_data(file_path):
    metadata_df = pd.read_csv(file_path, nrows=14, header=None, engine='python')
    telemetry_df = pd.read_csv(file_path, skiprows=14, low_memory=False)
    
    for col in telemetry_df.columns:
        telemetry_df[col] = pd.to_numeric(telemetry_df[col], errors='coerce')
    
    return metadata_df, telemetry_df

# Helper function to convert segment times
def convert_time_to_seconds(time_str):
    try:
        minutes, seconds = map(float, time_str.split(':'))
        return minutes * 60 + seconds
    except ValueError:
        return np.nan

# Helper function to extract fastest lap telemetry data
def get_fastest_lap_data(metadata_df, telemetry_df):
    segment_times_raw = metadata_df.iloc[12].values[1:]
    
    segment_times = [convert_time_to_seconds(time) for time in segment_times_raw if isinstance(time, str)]
    laps_array = [time for time in segment_times if 95 <= time <= 120]
    
    fastest_lap_time = min(laps_array)
    fastest_lap_index = segment_times.index(fastest_lap_time)
    
    start_time_stamp = sum(segment_times[:fastest_lap_index])
    end_time_stamp = sum(segment_times[:fastest_lap_index + 1])
    
    telemetry_FL = telemetry_df[(telemetry_df['Time'] >= start_time_stamp) & (telemetry_df['Time'] <= end_time_stamp)]
    
    start_distance = telemetry_FL['Distance on Vehicle Speed'].iloc[0]
    telemetry_FL['Distance'] = telemetry_FL['Distance on Vehicle Speed'] - start_distance
    
    return telemetry_FL

# Function to detect corners and straights
def identify_segments(telemetry_df, speed_threshold=80):
    segments = []
    current_segment = {'type': 'straight' if telemetry_df['Speed'].iloc[0] >= speed_threshold else 'corner', 'start': 0}
    
    for i in range(1, len(telemetry_df)):
        if telemetry_df['Speed'].iloc[i] < speed_threshold and current_segment['type'] == 'straight':
            current_segment['end'] = i - 1
            segments.append(current_segment)
            current_segment = {'type': 'corner', 'start': i}
        elif telemetry_df['Speed'].iloc[i] >= speed_threshold and current_segment['type'] == 'corner':
            current_segment['end'] = i - 1
            segments.append(current_segment)
            current_segment = {'type': 'straight', 'start': i}
    
    current_segment['end'] = len(telemetry_df) - 1
    segments.append(current_segment)
    
    return segments

# Function to determine the fastest segments and generate a track map
def generate_track_map(telemetry_FL_1, telemetry_FL_2, segments_1, segments_2, driver_1, car_1, driver_2, car_2):
    fig = go.Figure()

    # Plot Driver 1's segments
    for seg_1 in segments_1:
        avg_speed_1 = telemetry_FL_1['Speed'].iloc[seg_1['start']:seg_1['end'] + 1].mean()
        avg_speed_2 = telemetry_FL_2['Speed'].iloc[seg_1['start']:seg_1['end'] + 1].mean()

        color = 'blue' if avg_speed_1 > avg_speed_2 else 'red'

        fig.add_trace(go.Scattermapbox(
            lon=telemetry_FL_1['GPS Longitude'].iloc[seg_1['start']:seg_1['end'] + 1],
            lat=telemetry_FL_1['GPS Latitude'].iloc[seg_1['start']:seg_1['end'] + 1],
            mode='lines',
            name=f'{driver_1} Fastest' if color == 'blue' else driver_2,
            line=dict(width=4, color=color),
            hoverinfo='text',
            text=[
                f"{driver_1} Speed: {speed} km/h<br>Lat: {lat}<br>Lon: {lon}"
                for speed, lat, lon in zip(
                    telemetry_FL_1['Speed'].iloc[seg_1['start']:seg_1['end'] + 1],
                    telemetry_FL_1['GPS Latitude'].iloc[seg_1['start']:seg_1['end'] + 1],
                    telemetry_FL_1['GPS Longitude'].iloc[seg_1['start']:seg_1['end'] + 1]
                )
            ]
        ))

    # Plot Driver 2's segments
    for seg_2 in segments_2:
        avg_speed_1 = telemetry_FL_1['Speed'].iloc[seg_2['start']:seg_2['end'] + 1].mean()
        avg_speed_2 = telemetry_FL_2['Speed'].iloc[seg_2['start']:seg_2['end'] + 1].mean()

        color = 'red' if avg_speed_2 > avg_speed_1 else 'blue'

        fig.add_trace(go.Scattermapbox(
            lon=telemetry_FL_2['GPS Longitude'].iloc[seg_2['start']:seg_2['end'] + 1],
            lat=telemetry_FL_2['GPS Latitude'].iloc[seg_2['start']:seg_2['end'] + 1],
            mode='lines',
            name=f'{driver_2} Fastest' if color == 'red' else driver_1,
            line=dict(width=4, color=color),
            hoverinfo='text',
            text=[
                f"{driver_2} Speed: {speed} km/h<br>Lat: {lat}<br>Lon: {lon}"
                for speed, lat, lon in zip(
                    telemetry_FL_2['Speed'].iloc[seg_2['start']:seg_2['end'] + 1],
                    telemetry_FL_2['GPS Latitude'].iloc[seg_2['start']:seg_2['end'] + 1],
                    telemetry_FL_2['GPS Longitude'].iloc[seg_2['start']:seg_2['end'] + 1]
                )
            ]
        ))

    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            center=dict(lat=telemetry_FL_1['GPS Latitude'].mean(), lon=telemetry_FL_1['GPS Longitude'].mean()),
            zoom=16
        ),
        title="Track Map Comparison with Fastest Driver Highlighted",
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    fig.show()

# Function to prompt user to select two files
def select_files():
    Tk().withdraw()  # Close the root window
    print("Please select the first file:")
    file_path_car1 = askopenfilename()
    print(f"First file selected: {file_path_car1}")
    
    print("Please select the second file:")
    file_path_car2 = askopenfilename()
    print(f"Second file selected: {file_path_car2}")
    
    return file_path_car1, file_path_car2

# Main function to load data and plot the track
def main():
    file_path_car1, file_path_car2 = select_files()
    
    metadata_df_1, telemetry_df_1 = load_data(file_path_car1)
    metadata_df_2, telemetry_df_2 = load_data(file_path_car2)
    
    telemetry_FL_1 = get_fastest_lap_data(metadata_df_1, telemetry_df_1)
    telemetry_FL_2 = get_fastest_lap_data(metadata_df_2, telemetry_df_2)
    
    segments_1 = identify_segments(telemetry_FL_1)
    segments_2 = identify_segments(telemetry_FL_2)
    
    driver_name_car1 = metadata_df_1.iloc[3, 1]
    car_number_car1 = metadata_df_1.iloc[2, 1]
    driver_name_car2 = metadata_df_2.iloc[3, 1]
    car_number_car2 = metadata_df_2.iloc[2, 1]
    
    generate_track_map(telemetry_FL_1, telemetry_FL_2, segments_1, segments_2, driver_name_car1, car_number_car1, driver_name_car2, car_number_car2)

if __name__ == "__main__":
    main()
