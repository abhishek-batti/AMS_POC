import streamlit as st

if "resoltion" in st.session_state:
    with st.container(border=True) as main_container:
        st.title("Ticket Resolution")
        with st.container(border=True) as res_container:
            st.markdown(st.session_state.resolution)
else:
    with st.container(border=True) as main_container:
        st.title("Ticket Resolution")
        with st.container(border=True) as res_container:
            st.markdown("This is where ticket resolution details will be shown.")