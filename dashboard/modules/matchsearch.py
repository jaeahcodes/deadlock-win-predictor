import duckdb
import pandas as pd
import requests
import streamlit as st


DEADLOCK_HEROES = {
    1: "Infernus",
    2: "Seven",
    3: "Vindicta",
    4: "Lady Geist",
    6: "Abrams",
    7: "Wraith",
    8: "McGinnis",
    10: "Paradox",
    11: "Dynamo",
    12: "Kelvin",
    13: "Haze",
    14: "Holliday",
    15: "Bebop",
    16: "Calico",
    17: "Grey Talon",
    18: "Mo & Krill",
    19: "Shiv",
    20: "Ivy",
    25: "Warden",
    27: "Yamato",
    31: "Lash",
    35: "Viscous",
    50: "Pocket",
    52: "Mirage",
    58: "Vyper",
    60: "Sinclair",
    63: "Mina",
    64: "Drifter",
    65: "Venator",
    66: "Victor",
    67: "Paige",
    69: "The Doorman",
    72: "Billy",
    76: "Graves",
    77: "Apollo",
    78: "Deadman Danny",
    79: "Rem",
    80: "Silver",
    81: "Celeste",
    84: "Rat King",
    85: "Solomon",
    86: "Violet",
    87: "Nurse Harrow",
    88: "Baba",
}

UNRELEASED_HEROES = {
    21: "Kali",
    32: "Duo",
    34: "Akimbo",
    36: "Ballista",
    38: "Gunslinger",
    39: "The Boss",
    46: "Generic Person",
    53: "Fathom",
    54: "Cadence",
    56: "Bomber",
    68: "Boho",
    73: "Druid",
    74: "Graf",
    75: "Fortuna",
}

ALL_HEROES = {**DEADLOCK_HEROES, **UNRELEASED_HEROES}

con = duckdb.connect()

# function for searching matches under a given player
class matchSearcher:
    def __init__(self, con, accountID = None, matchID = None):
        self.con = con
        self.accountID = accountID
        self.matchID = matchID
    
    def findPlayerMatches(self, data, accountID = None):
        """
        This function pulls a list of matches for a given account ID
        It uses SQL to accomplish this grabbing only matches where the ID is present.
        
        Args:
            data (str): name of the DuckDB table containing match information
            accountID (int, optional): Players Steam ID to be matched in the table. Defaults to ID stored in class.
        
        Returns:
            pd.DataFrame: Match records containing match_id, duration_s,
                start_time, hero_id, and hero_name.
        """
        
        accountID = accountID if accountID is not None else self.accountID
        
        extracted_matches = self.con.execute(f"""
        SELECT match_id, duration_s, start_time, hero_id
        FROM {data}
        WHERE account_id = ?
        ORDER BY start_time DESC""", [accountID]).df()
        
        extracted_matches["hero_name"] = (
            extracted_matches["hero_id"]
            .map(ALL_HEROES)
            .fillna("Unknown Hero"))
        
        return extracted_matches
    
    def playerMatchInfo(self, data, accountID = None, matchID = None):
        """
        Pulls information from table only including data where the account_id is present.
        This is to be used for making graphs and displaying player stats such as Kills, Deaths, Networth, etc.
        
        Args:
            data (str): name of the DuckDB table containing match information
            accountID (int, optional): Players Steam ID to be matched in the table. Defaults to ID stored in class.
            matchID (int, optional): Numeric ID for a played match to be analyzed. Defaults to ID stored in class.
            
        Returns:
            pd.DataFrame: Match records containing all information, only where the accountID and matchID matches user input.
        """
        
        accountID = accountID if accountID is not None else self.accountID
        matchID = matchID if matchID is not None else self.matchID
        
        extracted_rows = self.con.execute(f"""
        SELECT *
        FROM {data}
        WHERE account_id = ?
        AND match_id = ?
        ORDER BY timestamp ASC""", [accountID, matchID]).df()
        
        return extracted_rows
    
    def modeledMatch(self, data, matchID = None):
        """
        Pulls all match information from the table associated with the accountID, and matchID.
        Used for modeling win rate over time, pulls all rows including the specified player.

        Args:
            data (str): name of the DuckDB table containing match information
            accountID (int, optional): Players Steam ID to be matched in the table. Defaults to ID stored in class.
            matchID (int, optional): Numeric ID for a played match to be analyzed. Defaults to ID stored in class.
            
        Returns:
            pd.DataFrame: Match records containing all information for a given match.
        """
        
        matchID = matchID if matchID is not None else self.matchID
        
        modeled_rows = self.con.execute(f"""
        SELECT *
        FROM {data} 
        WHERE match_id = ?
        """, [matchID]).df()
        
        return modeled_rows