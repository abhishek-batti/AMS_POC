import streamlit as st

if ("Specific Resolution" in st.session_state) and ("General Resolution" in st.session_state):
    with st.container(border=True) as main_container:
        st.title("Ticket Resolution (Specific)")
        with st.container(border=True) as sres_container:
            st.json(st.session_state["Specific Resolution"])
        with st.container(border=True) as gres_container:
            st.json(st.session_state["General Resolution"])
else:
    with st.container(border=True) as main_container:
        st.title("Ticket Resolution")
        with st.container(border=True) as res_container:
            st.markdown("This is where ticket resolution details will be shown.")