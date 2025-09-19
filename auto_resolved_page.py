import streamlit as st
from datetime import datetime

def page():
    # Sample ticket details
    if "ticket" in st.session_state:
        ticket = st.session_state["ticket"]
    else:
        ticket = None
    # Page config
    st.set_page_config(page_title="Ticket Resolution", page_icon="✅", layout="centered")

    # Header
    st.title("🤖 Ticket Auto-Resolved")
    st.write("This ticket has been automatically resolved by the AI bot.")

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

    # Resolution Note
    st.success("✅ Resolution Applied: Password reset completed successfully by the bot.")

    # Footer
    st.markdown("---")
    st.caption("AI-powered ITSM | Auto-resolution workflow demo")
