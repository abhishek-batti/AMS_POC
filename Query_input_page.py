import streamlit as st
from classes.ticket import Ticket
import joblib
import json

def classify_category(description: str) -> str:
    loaded_model = joblib.load("models\svm_tfidf_pipeline.pkl")
    preds = loaded_model.predict([description])
    with open("mappings\\label_mappings.json") as f:
        mappings = json.load(f)
    id2label_loaded = mappings["id2label"]
    preds = loaded_model.predict([description])
    class_preds = [id2label_loaded[str(p)] for p in preds]
    return class_preds[0].split("/")

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
                classification = classify_category(user_query)
                st.write(f"Predicted Category: {classification}")
                ticket.category = classification[0]
                ticket.sub_category = classification[1]
                st.success("Ticket created successfully!")
                st.session_state["ticket"] = ticket
                
if __name__ == "__main__":
    query_input_page()