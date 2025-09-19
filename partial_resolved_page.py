import streamlit as st

def page():
    # Page setup
    st.set_page_config(page_title="Resolution", layout="wide")

    # Example ticket details
    if "ticket" in st.session_state:
        ticket = st.session_state["ticket"]
    else:
        ticket = None
    # -------------------------
    # Custom CSS for Professional Look
    # -------------------------
    st.markdown("""
    <style>
        .card {
            background: #ffffff;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .ticket-summary {
            background: linear-gradient(135deg, #f9fafb, #f3f4f6);
            border-left: 6px solid #2563eb;
        }
        .workflow-step {
            border-left: 4px solid #e5e7eb;
            margin: 15px 0;
            padding: 15px 20px;
            border-radius: 8px;
            background: #fafafa;
            position: relative;
        }
        .workflow-step::before {
            content: "●";
            position: absolute;
            left: -12px;
            color: #2563eb;
            font-size: 20px;
        }
        .ai {
            border-left-color: #2563eb;
            background: #f0f7ff;
        }
        .human {
            border-left-color: #dc2626;
            background: #fff5f5;
        }
        .step-title {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 6px;
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }
        .success { background: #27ae60; color: white; }
        .warning { background: #f39c12; color: white; }
        .error { background: #c0392b; color: white; }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------
    # Ticket Summary
    # -------------------------
    st.title("🤝 Ticket Resolution Workflow")

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

        # -------------------------
        # Workflow Steps
        # -------------------------
        
        if "Resolution" in st.session_state:
            st.subheader("📍 Resolution Journey")
            resolution = st.session_state["Resolution"]
            for step in resolution["steps"]:
                if step.lower() == "escalate to human staff":
                    st.markdown(f"""
                                <div class="workflow-step ai">
                                    <div class="step-title">🤖 Step 4: Assigning Support Staff <span class="badge success">Suppport staff Assigned</span></div>
                                    Assigned to <b>{ticket.assignment_group}</b>.
                                </div>

                                <div class="workflow-step human">
                                    <div class="step-title">👨‍💻 Step 5: Support Team is working on resolution <span class="badge warning">In Progress</span></div>
                                    Assigned to <b>{ticket.assignment_group}</b>. Resolution in progress.
                                </div>
                                """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                                <div class="workflow-step ai">
                                    <div class="step-title">🤖 Step 1: {step} <span class="badge success">Success</span></div>
                                    
                                </div>
                                
                                """, unsafe_allow_html=True)
            
            