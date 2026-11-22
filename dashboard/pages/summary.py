import streamlit as st


# removes awkward padding before the title
st.markdown(
    body="""
        <style>
            .block-container{
                    padding-top: 25px;
                }
        </style>
    """, 
    unsafe_allow_html = True
)

st.set_page_config(
    page_title="Deadlock Match Analysis",
    layout="wide"
)

# creating page resembling poster symposium style presentation for our results
st.title("Predicting Deadlock Match Outcomes", text_alignment = "center")
st.caption(
    "Capstone Project | University of Michigan "
    "Master of Applied Data Science",
    text_alignment = "center"
)

st.caption(
    "Jaeah Kim | Carter Pasternak | Taha Ziad",
    text_alignment = "center"
)


#INTRO
st.markdown("---")


col1, col2, col3 = st.columns(3, gap="large")

with col1:
    with st.container(border = True):
        st.subheader("Introduction")
        st.write("""
        - Research motivation
        - Project objectives
        - Research questions
        """)

with col2:
    with st.container(border = True):
        st.subheader("Data Sources")
        st.write("""
        - Deadlock match data
        - Player performance statistics
        - Match outcome information
        """)

with col3:
    with st.container(border = True):
        st.subheader("Exploratory Analysis")
        st.write("""
        - Dataset characteristics
        - Player performance distributions
        - Trends across match outcomes
        """)
    
    
#METHODS
st.markdown("---")

method1, method2, method3 = st.columns(3, gap="large")

with method1:
    with st.container(border = True):
        st.subheader("Methods")
        st.write("""
            - Explain how we did it
            -
            -
            """)
    
with method2:
    with st.container(border = True):
        st.subheader("Results")
        
        fig1, fig2, fig3 = st.columns(3)
        
        with fig1:
            st.image("", use_container_width = True)
            st.caption("Figure 1 explanation")
        
        with fig2:
            st.image("", use_container_width = True)
            st.caption("Figure 2 explanation")
        
        with fig3:
            st.image("", use_container_width = True)
            st.caption("Figure 3 explanation")
    
with method3:
    with st.container(border = True):
        st.subheader("Conclusions")
        st.write("""
            - Conclude
            -
            -
            """)
    

