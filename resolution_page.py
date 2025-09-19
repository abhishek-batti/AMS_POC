import streamlit as st
import partial_resolved_page
import auto_resolved_page
import alloted_issue_page

if ("Resolution" in st.session_state):
    resolution = st.session_state["Resolution"]
    if resolution["Solvability"] == "partially automated":
        partial_resolved_page.page()
    elif resolution["Solvability"] == "automated":
        auto_resolved_page.page()
    elif resolution["Solvability"] == "unsolvable":
        alloted_issue_page.page()
    else:
        st.json(resolution)
        
else:
    st.write("No resolutions present")