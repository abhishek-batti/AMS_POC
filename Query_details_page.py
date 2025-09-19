import streamlit as st
from classes.ticket import Ticket
from classifyAndResolve import resolve_ticket_general, resolve_ticket_specific, resolve_ticket
from RAG import RAGRetriever
import json
# -------------------------
# Custom CSS
# -------------------------
st.markdown("""
    <style>
    .ticket-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 14px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        margin-top: 20px;
    }
    .ticket-header {
        font-size: 22px;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 20px;
    }
    .ticket-field {
        font-size: 16px;
        margin: 10px 0;
        line-height: 1.5;
    }
    .ticket-label {
        font-weight: 600;
        color: #34495e;
    }
    .status-open {
        background: #27ae60;
        color: white;
        padding: 3px 10px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
    }
    .status-pending {
        background: #f39c12;
        color: white;
        padding: 3px 10px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
    }
    .status-closed {
        background: #c0392b;
        color: white;
        padding: 3px 10px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
    }
    .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)


# -------------------------
# Render Ticket Details
# -------------------------
def render_ticket(ticket: Ticket):
    # Convert values to safe strings
    status = str(ticket.status)
    raised_on = str(ticket.raised_on)
    category = str(ticket.category)
    sub_category = str(ticket.sub_category)
    priority = str(ticket.priority)
    assignment_group = str(ticket.assignment_group)
    description = str(ticket.description)

    # Badge style for status
    status_class = "status-open"
    if status.lower() == "closed":
        status_class = "status-closed"
    elif status.lower() == "pending":
        status_class = "status-pending"

    # Ticket card
    st.markdown(f"""
    <div class='ticket-card'>
        <div class='ticket-header'>🎫 Ticket Details</div>
        <div class="ticket-field"><span class="ticket-label">📂 Status:</span> <span class="{status_class}">{status}</span></div>
        <div class="ticket-field"><span class="ticket-label">📅 Raised On:</span> {raised_on}</div>
        <div class="ticket-field"><span class="ticket-label">🏷️ Category:</span> {category}</div>
        <div class="ticket-field"><span class="ticket-label">🔖 Sub Category:</span> {sub_category}</div>
        <div class="ticket-field"><span class="ticket-label">⚡ Priority:</span> {priority}</div>
        <div class="ticket-field"><span class="ticket-label">👥 Assignment Group:</span> {assignment_group}</div>
    </div>
    """, unsafe_allow_html=True)

    # User Query
    st.markdown("<div class='section-title'>📝 User Query</div>", unsafe_allow_html=True)
    st.text_area("User Query", value=description, height=140, disabled=True, label_visibility="collapsed")

    # Resolution button
    if st.button("💡 Generate Resolution", use_container_width=True):
        with st.status("⚙️ Working on resolution..."):
            ticket_text = st.session_state.ticket.print_ticket()
            st.write("Retriving Relevant Docs from knowledge base...")
            retriever = RAGRetriever()
            results = retriever.query(description, top_k=4)
            print(json.dumps(results, indent=2, ensure_ascii=False)[:10000])
            st.write("Creating context...")
            context = retriever.get_prompt_text(results, max_chars=3500)[:5000]
            st.write("Solving...")
            resolution = resolve_ticket(description, context)
            st.session_state["Resolution"] = resolution
            st.success("✅ Resolutions generated successfully!")

    if ("Resolution" in st.session_state):
        st.info("📑 Resolution is Ready. Navigate to the **Resolution** page to review them.")


# -------------------------
# Page Content
# -------------------------
st.title("📋 Ticket Query Details")
st.markdown(
    "Here you can review the details of your submitted ticket. "
    "Our system has neatly captured all key information for easy reference."
)
st.divider()

if "ticket" in st.session_state:
    render_ticket(st.session_state.ticket)
else:
    st.info("⚠️ No ticket available. Please create a ticket first.")
