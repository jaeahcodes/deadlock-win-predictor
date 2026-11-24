import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

file_path = "/Users/taha/Desktop/Capstone/deadlock_ranked_20m_last_week.parquet"
match_data = pl.read_parquet(file_path)

print(f"Loaded {len(match_data)} matches. Team 0 win rate: {match_data['team0_won'].mean():.4f}")

match_data = match_data.with_columns([
    # soul diff (difference in nw between teams)
    (pl.col("team0_souls_20m") - pl.col("team1_souls_20m")).alias("souls_diff"),
    # soul ratio / share
    (pl.col("team0_souls_20m") / (pl.col("team0_souls_20m") + pl.col("team1_souls_20m") + 1e-5)).alias("souls_ratio"),
    # combat assists
    (pl.col("team0_assists_20m") - pl.col("team1_assists_20m")).alias("assists_diff"),
    # farm & lane control
    (pl.col("team0_creeps_20m") - pl.col("team1_creeps_20m")).alias("creeps_diff"),
    (pl.col("team0_denies_20m") - pl.col("team1_denies_20m")).alias("denies_diff"),
    # damage, levels, objs
    (pl.col("team0_damage_20m") - pl.col("team1_damage_20m")).alias("damage_diff"),
    (pl.col("team0_level_20m") - pl.col("team1_level_20m")).alias("level_diff"),
    (pl.col("team0_objectives_taken_20m") - pl.col("team1_objectives_taken_20m")).alias("obj_diff"),
])

feature_cols = [
    #"souls_diff",
    #"souls_ratio",
    "assists_diff",
    "creeps_diff",
    "denies_diff",
    "damage_diff",
    #"level_diff",
    "obj_diff",
]

X = match_data.select(feature_cols).to_numpy()
y = match_data["team0_won"].to_numpy()

model = HistGradientBoostingClassifier(
    max_iter=150,
    max_depth=4,
    learning_rate=0.03,
    l2_regularization=1.0,
    random_state=42,
)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
auc_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
print(f"\n5-Fold CV ROC-AUC: {auc_scores.mean():.4f} (+/- {auc_scores.std():.4f})")

# holdout split so importance isn't evaluated on train data
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
model.fit(X_train, y_train)

perm = permutation_importance(model, X_val, y_val, n_repeats=5, random_state=42, scoring="roc_auc")

importance_df = (
    pl.DataFrame({
        "feature": feature_cols,
        "importance_mean": perm.importances_mean,
        "importance_std": perm.importances_std,
    })
    .sort("importance_mean", descending=True)
)

print("\nFeature Importances (val ROC-AUC drop):")
print(importance_df)