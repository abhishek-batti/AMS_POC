import streamlit as st
from datetime import datetime

# Sample ticket details
def page():
    if "ticket" in st.session_state:
        ticket = st.session_state["ticket"]
    else:
        ticket = None

    # Page config
    st.set_page_config(page_title="Ticket Escalation", page_icon="⚠️", layout="centered")

    # Header
    st.title("🤖 Ticket Requires Human Intervention")
    st.warning("The AI bot could not determine the resolution steps for this ticket. It has been escalated to the IT team.")

    # Ticket Card
    if ticket is not None:
        st.markdown(f"""
        <div class="card ticket-summary">
            <h4>🎫 Ticket Summary</h4>
            <p><b>Status:</b> {ticket.status} <br>
            <b>Raised On:</b> {ticket.raised_on} <br>
            <b>Category:</b> {ticket.category} → {ticket.sub_category} <br>
            <b>Priority:</b> {ticket.priority} <br>
            <b>Assignment Group:</b> {ticket.assignment_group} <br>
            <b>User Query:</b> {ticket.description}</p>
        </div>
        """, unsafe_allow_html=True)

    # Escalation Note
    st.error("⚠️Note: Ticket could not be resolved autonomously. A human IT Agent will take over to provide resolution.")

    # Footer
    st.markdown("---")
    st.caption("AI-powered ITSM | Ticket Escalation Workflow Demo")
