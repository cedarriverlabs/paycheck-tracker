import streamlit as st

st.set_page_config(
    page_title="Paycheck Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Paycheck Tracker")
st.write("If you can see this, the app is loading correctly.")

st.divider()

st.subheader("Login")

with st.form("login"):
    username = st.text_input("Username", value="doug")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Log in")

    if submitted:
        if username == "doug" and password == "change-me":
            st.success("Login successful! The full app will be restored next.")
            st.balloons()
        else:
            st.error("Wrong username or password")
