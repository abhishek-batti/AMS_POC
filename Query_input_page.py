import streamlit as st
from classes.ticket import Ticket

def query_input_page():
    with st.container() as con:
        st.title("Ticket Query Input Page")
        if "ticket" in st.session_state:
            st.info("A ticket has already been created. Navigate to the 'Ticket Details' page to view it.")
            ticket_text = st.session_state.ticket.description
        with st.form(key="query_form") as form:
            user_query = st.text_area("Enter your Query here:", ticket_text if "ticket" in st.session_state else "", height=200)
            submitted = st.form_submit_button("Submit")
            if submitted and user_query.strip():
                ticket = Ticket(description=user_query)
                st.success("Ticket created successfully!")
                st.session_state["ticket"] = ticket
if __name__ == "__main__":
    query_input_page()