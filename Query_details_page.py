import streamlit as st
from classes.ticket import Ticket

# -------------------------
# Custom CSS for styling
# -------------------------
st.markdown("""
    <style>
    .ticket-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        margin-top: 15px;
    }
    .ticket-header {
        font-size: 20px;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 15px;
    }
    .ticket-field {
        font-size: 16px;
        margin: 8px 0;
        line-height: 1.4;
    }
    .ticket-label {
        font-weight: 600;
        color: #34495e;
    }
    </style>
""", unsafe_allow_html=True)

def render_ticket(ticket):
    # Status badge class
    status_class = "status-open"
    if ticket.status.lower() == "closed":
        status_class = "status-closed"
    elif ticket.status.lower() == "pending":
        status_class = "status-pending"

    with st.container(border=True) as main_container: 
        with st.container(border=True) as header_container:
            st.markdown(f"<div class='ticket-header'>🎫 Ticket Details</div>", unsafe_allow_html=True)
        
        with st.container(border=True) as status_container:
            st.markdown(f"""
            
                <div class="ticket-field"><span class="ticket-label">📂 Status:</span> <span class="{status_class}">{ticket.status}</span></div>
                <div class="ticket-field"><span class="ticket-label">📅 Raised On:</span> {ticket.raised_on}</div>
                <div class="ticket-field"><span class="ticket-label">🏷️ Category:</span> {ticket.category}</div>
                <div class="ticket-field"><span class="ticket-label">🔖 Sub Category:</span> {ticket.sub_category}</div>
            
            """, unsafe_allow_html=True)

        # --- Non-editable text fields for long text ---
        with st.container(border=True) as _: 
            st.markdown("**📝 User Query:**")
            with st.container() as user_query_container:
                st.text(ticket.description)
        with st.container(border=True) as _:
            st.markdown("**📌 Short Description:**")
            with st.container() as short_desc_container:
                st.text(ticket.short_description)

        # --- Remaining fields ---





    # -------------------------
    # Main Page Layout
    # -------------------------
st.title("📋 Ticket Query Details")

st.markdown(
    "Here you can review the details of your submitted ticket. "
    "Our system has captured all key information for easy reference."
)

st.divider()

if "ticket" in st.session_state:
    ticket = st.session_state.ticket
    render_ticket(ticket)
else:
    st.info("⚠️ No ticket available. Please create a ticket first.")
