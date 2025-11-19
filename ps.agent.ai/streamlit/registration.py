import hashlib

import streamlit as st
from sqlalchemy import text, false
import logging
from passlib.hash import bcrypt_sha256

# Enable SQLAlchemy engine logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

conn = st.connection("bldTestVault",type="sql")
query = text("""
    INSERT INTO user_registration (firstname, lastname, username, user_password, email, dob, mobile)
    VALUES (:firstname, :lastname, :username, :user_password, :email, :dob, :mobile)
            """)
with st.form("registration_form",clear_on_submit=False):
    st.subheader("Registration Forms")
    firstname=st.text_input("Enter your First Name")
    lastname=st.text_input("Enter your Last Name")
    username=st.text_input("Enter your Username")
    user_password=st.text_input("Enter your Password",type="password")
    email=st.text_input("Enter your Email")
    dob=st.date_input("Enter Date of Birth")
    mobile=st.text_input("Enter Mobile Number")
    submit_btn= st.form_submit_button("Register")

    if submit_btn:
        if not firstname or not lastname or not username or not user_password or not email or not dob or not mobile:
            st.warning("Please fill all mandatory fields")
        else:
            try:
                with conn.session.begin():

                    result = conn.session.execute(query, {
                        "firstname": firstname,
                        "lastname": lastname,
                        "username": username,
                        "user_password": user_password,
                        "email": email,
                        "dob": str(dob),
                        "mobile": mobile
                    })
                    logging.info(f"Rows affected: {result.rowcount}")
                    conn.session.commit()
                st.success(f"✅ User '{username}' registered successfully!")
            except Exception as e:
                st.error(f"Database Error: {e}")

st.divider()
if st.checkbox("Show Registered Users"):
    df = conn.query("SELECT id, firstname, lastname, username, email, dob, mobile, createdDate FROM user_registration;")
    st.dataframe(df)