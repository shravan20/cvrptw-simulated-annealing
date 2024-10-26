import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
import json

loc = [[18.867962678748306, 83.02193878023306]]
st.title("ULIP HACKATHON")
# File uploader widget
uploaded_file = st.file_uploader("Choose a CSV file")

if uploaded_file is not None:
    # Read the CSV file into a DataFrame
    dataframe = pd.read_csv(uploaded_file)
    
    # Display the DataFrame
    st.write("DataFrame:", dataframe)

    # Convert DataFrame to JSON
    json_data = dataframe.to_json(orient="records")  # Convert to JSON format

    # Parse JSON string for pretty printing
    parsed_json = json.loads(json_data)
    
    # Display JSON
    st.write("JSON Data:", json.dumps(parsed_json, indent=4))

result = st.button("RUN");
if result:
    df = pd.DataFrame(
        loc
    ,
    columns=["lat", "lon"],
    )
    st.map(df)