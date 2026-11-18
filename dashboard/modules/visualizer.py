import numpy as np 
import matplotlib.pyplot as plt 
import streamlit as st

# creating functions for visualizing
class deadlockVisualizer:
    def __init__(self, matchID = None, accountID = None):
    
    # start by initializing data so match_id is none
    # this prevents graphing as matches are associated with ID
        self.matchID = matchID
        self.accountID = accountID
    
    def plotWinChance(self, prob, min, team, winner):
        """
        Plots the win chance of a team over time. 
        Uses the match_id, probability, minutes, team of a player,
        and true winner to show the outcome.
        Prob, min, and winner are to be found using the module for predicting probability of win chance.
        
        Args:
            prob (array): Array of win probability, found after modeling.
            min (array): Array of minutes from match, found after modeling.
            team (int): Team that the player belongs to.
            winner (int): Team that won the game.
        
        Returns:
            Plotted win chance over the course of a game
        """
        
        fig, ax = plt.subplots(figsize = (10,4))
        ax.plot(min, prob, marker='o', color='#1f77b4', linewidth=2.5, label='Team 0 Win Probability')
        ax.axhline(0.5, color='gray', linestyle='--', alpha=0.7)
        ax.fill_between(min, 0.5, prob, where=(np.array(prob) >= 0.5), color='#1f77b4', alpha=0.15)
        ax.fill_between(min, 0.5, prob, where=(np.array(prob) < 0.5), color='#d62728', alpha=0.15)
        ax.title(f'Win Probability Curve — Match {self.match_id} (Actual Winner: {winner})', fontsize=13, fontweight='bold')
        ax.xlabel('Match Time (Minutes)', fontsize=11)
        ax.ylabel(f'Team {team} Win Probability', fontsize=11)
        ax.ylim(0, 1)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        
        return fig
    
    def plotPlayerStats(self, min, stat):
        """
        Creates a plot for a player with a given stat over time of a match.
        
        Min is the minute during the game the stat happened, stat is the requested stat.
        This allows for a player to use data from a given match and track data such as kills over time.
        
        Args:
            min (array): Array of minutes (or time frame) from match.
            stat (array): Array of a chosen statistic to be plotted on a graph.
        
        Returns:
            Plotted statistic over the course of a match, i.e. kills over time.
        """
        fig, ax = plt.subplots(figsize = (10,4))
        ax.plot(min, stat, marker='o', color='#1f77b4', linewidth=2.5)
        ax.axhline(0.5, color='gray', linestyle='--', alpha=0.7)
        ax.title(f'{stat}s Over Time of a Match', fontsize=13, fontweight='bold')
        ax.xlabel('Match Time (Minutes)', fontsize=11)
        ax.ylabel(f'{stat}s', fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.5)
        return fig
