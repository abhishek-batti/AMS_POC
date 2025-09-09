import streamlit as st

if "current_page" not in st.session_state:
    st.session_state.current_page = "Tickets:Query_input_page.py"

pages = {
    "Tickets" : [
        st.Page("Query_input_page.py", title="Ticket Query Input"),
        st.Page("Query_details_page.py", title="Ticket Details"),
        st.Page("resolution_page.py", title="Ticket Resolution")
    ]
}

pg = st.navigation(pages)
pg.run()