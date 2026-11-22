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

# creating page discussing "paper" details, i.e. report like analysis
st.title("Predicting Deadlock Match Outcomes")

st.markdown("""
## Introduction

Begin by talking about Deadlock as a game
Talk about major gameplay elements, the competitive scene, and ways to win in-game
Mention different ways in which the game can be altered, and tides are turned, causing wins/losses

Introduce websites like Statlocker, Deadlock-API, and others
Bring up what they do, how they can help users, and what they leave out

Talk about the Dota 2 project we were inspired by; mention how we want to do something similar
Bridge into our project, methods, and introduce methods and outcomes

Explain how a predictive model can help understand meta game strategies and gaps
Describe how correlatory features can create a framework for improving at Deadlock let alone any game. 
Describe how utilizing player data can help direct balance decisions within development.

## Methods

Create a baseline binary classifier on simple aggregate team stats around a generalized midpoint of an average game. 	
This is used for comparison further. 

Develop a model that considers game stats at regular intervals, and map the feature importance at these intervals. 
Create features that are independent of the main stat (Souls in this case) still result in strong importance and accurate predictions. 

## Results

Elaborate on how successful the prediction is and what features stand out the most. 
Discuss the feature set in regards to how players/heroes/teams interact with them. 

Weigh features based on magnitude, assign an influence or “impact” generalized score to each player given their contribution to the most important features.
Develop this further into a system to contextualize player performance.
Reach: Provide a dynamic dashboard that shows our realtime impact approximation of a player at given times (why they gained/lost impact, what actions could have improved it, or degraded it.


## Discussion

Reflect back on the original Dota 2 inspiration. 
What did we miss from that original scope?
How did we improve from that original scope?
What limitations could have helped us take it further?

Generalize this approach into a systemic method for understanding meta games and game balance for any game.
Provide how we’d approach a change to Deadlock given our understanding. 
Hero rework
Objective rebalance""")


