
import streamlit as st
st.markdown("# Main page 🎈")
st.sidebar.markdown("# Main page 🎈")
conn = st.connection("bldTestVault")
df = conn.query("select * from accountTable")
st.dataframe(df)