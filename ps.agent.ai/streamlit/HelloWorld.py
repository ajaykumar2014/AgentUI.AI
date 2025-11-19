import streamlit as st
import pandas as pd
import numpy as np




main_page = st.Page("home_page.py", title="Home", icon="🎈")
page_2 = st.Page("database_connection.py", title="Database Connection", icon="❄️")
page_3 = st.Page("session.py", title="Session", icon="🎉")
page_4 = st.Page("color-picker.py", title="Color Picker", icon="🎉")
page_5 = st.Page("registration.py", title="User Registration", icon="🎉")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_5])

# Run the selected page
pg.run()