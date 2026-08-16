import streamlit as st

st.set_page_config(page_title="Paycheck Tracker", page_icon="💰")

st.title("💰 Paycheck Tracker")
st.write("If you can see this message, the app is working.")

st.divider()

username = st.text_input("Username", value="doug")
password = st.text_input("Password", type="password")

if st.button("Log in"):
    if username == "doug" and password == "change-me":
        st.success("Login works!")
        st.balloons()
    else:
        st.error("Wrong credentials")
