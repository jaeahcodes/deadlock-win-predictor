import numpy as np 
import matplotlib.pyplot as plt 
import streamlit as st

# creating functions for visualizing
class deadlockVisualizer:
    def __init__(self, matchID = None):
    
    # start by initializing data so match_id is none
    # this prevents graphing as matches are associated with ID
        self.matchID = matchID
    
    def plotWinChance(matchID, prob, min, team, winner):
        """
        Plots the win chance of a team over time. 
        Uses the match_id, probability, minutes, team of a player,
        and true winner to show the outcome.
        Prob, min, and winner are to be found using the module for predicting probability of win chance.
        
        Args:
            matchID (int): ID of the match being plotted
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
        ax.set_title(f'Win Probability Curve — Match {matchID} (Actual Winner: {winner})', fontsize=13, fontweight='bold')
        ax.set_xlabel('Match Time (Minutes)', fontsize=11)
        ax.set_ylabel(f'Team {team} Win Probability', fontsize=11)
        ax.set_ylim(0, 1)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        
        return fig
    
    # plots individual stats
    def plotPlayerStats(min, stat, stat_name):
        """
        Creates a plot for a player with a given stat over time of a match.
        
        Min is the minute during the game the stat happened, stat is the requested stat.
        This allows for a player to use data from a given match and track data such as kills over time.
        
        Args:
            min (array): Array of minutes (or time frame) from match.
            stat (array): Array of a chosen statistic to be plotted on a graph.
            stat_name (string): Name of the stat being plotted.
        
        Returns:
            Plotted statistic over the course of a match, i.e. kills over time.
        """
        
        fig, ax = plt.subplots(figsize = (6,3))
        ax.plot(min, stat, marker='.', color='#1f77b4', linewidth=1.5)
        ax.set_title(f'{stat_name} Over Match Duration', fontsize=12, fontweight='bold')
        ax.set_xlabel('Match Time (Minutes)', fontsize=11)
        ax.set_ylabel(f'{stat_name}', fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.5)
        return fig

    def plotNetworth(df, min = "minutes",
                    networth = "player_net_worth",
                    kills = "gold_players",
                    laning = "gold_laning",
                    neutral = "gold_neutral",
                    boss = "gold_bosses",
                    treasure = "gold_treasure",
                    denies = "gold_denied"):
        
        fig, ax = plt.subplots(figsize = (10,6))
        
        # stacking gold sources for graph
        sources = [kills, laning, neutral, boss, treasure, denies]
        labels = ["Players", "Laning", "Neutral", "Boss", "Treasure", "Denies"]
        colors = ["#49a467", "#2e7360", "#2e7312", "#4c8f31", "#92d277", "#57c22d"]
        
        ax.stackplot(
            df[min],
            [df[source] for source in sources],
            labels = labels,
            colors = colors,
            alpha = 0.75
        )
        
        ax.plot(
            df[min],
            df[networth],
            color = "#222222",
            linewidth = 1.5,
            label = "Total Net Worth"
        )
        
        ax.set_title("Net Worth and Sources over Match Duration", fontsize=12, fontweight='bold')
        ax.set_xlabel('Match Time (Minutes)', fontsize=11)
        ax.set_ylabel("Souls / Gold", fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.4)
        ax.legend(loc = "upper left")
        return fig
        