import streamlit as st
from classes.ticket import Ticket
import joblib
import json
from classifyAndResolve import classify_ticket


# --- Classification Function ---
def classify_category(description: str) -> str:
    loaded_model = joblib.load("models/svm_tfidf_pipeline.pkl")
    preds = loaded_model.predict([description])

    with open("mappings/label_mappings.json") as f:
        mappings = json.load(f)

    id2label_loaded = mappings["id2label"]
    preds = loaded_model.predict([description])
    class_preds = [id2label_loaded[str(p)] for p in preds]

    return class_preds[0].split("/")


# --- Page Layout ---
def query_input_page():
    st.set_page_config(page_title="Ticket Assistant", page_icon="🎫", layout="centered")

    # Header
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: #2C3E50;
            text-align: center;
            margin-bottom: 1rem;
        }
        .subtitle {
            font-size: 1rem;
            color: #7F8C8D;
            text-align: center;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="main-title">🎫 Ticket Query Assistant</div>', unsafe_allow_html=True)


    # Query Form
    with st.form(key="query_form"):
        st.markdown("### ✍️ Enter your Query")
        user_query = st.text_area(
            "Provide details about your issue:",
            st.session_state.ticket.description if "ticket" in st.session_state else "",
            height=150,
            placeholder="e.g., Unable to connect to VPN after update..."
        )

        submitted = st.form_submit_button("🚀 Create Ticket")

        if submitted and user_query.strip():
            ticket = Ticket(description=user_query)

            with st.spinner("🔍 Classifying your ticket..."):
                classification = classify_category(user_query)
                ticket.category = ''.join(classification[:-1])
                ticket.sub_category = classification[-1]

            with st.spinner("👥 Assigning to the right group..."):
                response = classify_ticket(ticket.print_ticket())
                assignment_group = response.get("assignment_group")
                priority = response.get("priority")
                ticket.assignment_group = assignment_group
                ticket.priority = priority

            st.success("✅ Ticket created successfully!")

            # Display ticket details in a nice card
            with st.container():
                st.markdown("### 📌 Ticket Summary")
                st.markdown(
                    f"""
                    <div style="background-color:#F9F9F9; padding:15px; border-radius:10px; border:1px solid #ddd;">
                        <b>Description:</b> {ticket.description}<br>
                        <b>Category:</b> {ticket.category} → {ticket.sub_category}<br>
                        <b>Assignment Group:</b> {ticket.assignment_group}<br>
                        <b>Priority:</b> {ticket.priority}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.session_state["ticket"] = ticket

    if "ticket" in st.session_state:
        st.info("ℹ️ A ticket already exists. Go to the **Ticket Details** page to view it.")


if __name__ == "__main__":
    query_input_page()
