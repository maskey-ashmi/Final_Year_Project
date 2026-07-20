# random_forest_from_scratch.py
"""
Random Forest implementation from first principles.
Trains on the synthetic acne dataset generated earlier and evaluates the model.

Only NumPy and Pandas are used for data handling. Scikit‑learn utilities are limited to
train_test_split, LabelEncoder and evaluation metrics as required.
"""

import os
import pickle
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
try:
    import pandas as pd
except Exception:
    pd = None  # Pandas is only needed for training; safe to ignore for inference
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def gini(y: np.ndarray) -> float:
    """Compute Gini impurity for an array of class labels.

    Parameters
    ----------
    y: np.ndarray
        1‑D array of integer class labels.
    """
    if y.size == 0:
        return 0.0
    _, counts = np.unique(y, return_counts=True)
    probs = counts / y.size
    return 1.0 - np.sum(probs ** 2)


def most_common_label(y: np.ndarray) -> Any:
    """Return the most frequent label in *y* (break ties by smallest value)."""
    counter = Counter(y)
    return min(counter, key=lambda k: (-counter[k], k))

# -----------------------------------------------------------------------------
# Tree node definition
# -----------------------------------------------------------------------------
class Node:
    """A node in the decision tree.

    Attributes
    ----------
    feature_index: Optional[int]
        Index of the feature used for splitting. ``None`` for leaf nodes.
    threshold: Optional[float]
        Threshold value for the split. ``None`` for leaf nodes.
    left: Optional[Node]
        Left child (samples where feature <= threshold).
    right: Optional[Node]
        Right child (samples where feature > threshold).
    value: Optional[int]
        Predicted class for leaf nodes.
    gini: float
        Gini impurity of the node (useful for feature‑importance).
    n_samples: int
        Number of training samples that reached the node.
    """

    def __init__(
        self,
        feature_index: Optional[int] = None,
        threshold: Optional[float] = None,
        left: Optional["Node"] = None,
        right: Optional["Node"] = None,
        *,
        value: Optional[int] = None,
        gini: float = 0.0,
        n_samples: int = 0,
    ) -> None:
        self.feature_index = feature_index
        self.threshold = threshold
        self.left = left
        self.right = right
        self.value = value
        self.gini = gini
        self.n_samples = n_samples

    def is_leaf(self) -> bool:
        return self.value is not None

# -----------------------------------------------------------------------------
# Decision Tree implementation
# -----------------------------------------------------------------------------
class DecisionTree:
    """A CART decision tree using Gini impurity.

    Parameters
    ----------
    max_depth: int, default=10
        Maximum depth of the tree.
    min_samples_split: int, default=2
        Minimum number of samples required to attempt a split.
    min_samples_leaf: int, default=1
        Minimum number of samples required in a leaf node.
    max_features: Optional[int]
        Number of features to consider when looking for the best split. If ``None``
        all features are considered.
    random_state: Optional[int]
        Seed for reproducibility.
    """

    def __init__(
        self,
        max_depth: int = 10,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: Optional[int] = None,
        random_state: Optional[int] = None,
    ) -> None:
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.random_state = random_state
        self.root: Optional[Node] = None
        # feature_importances_ will store summed impurity decrease per feature
        self._feature_importances: defaultdict = defaultdict(float)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray) -> "DecisionTree":
        """Build a decision tree from the training data.

        Parameters
        ----------
        X: np.ndarray, shape (n_samples, n_features)
        y: np.ndarray, shape (n_samples,)
        """
        if self.random_state is not None:
            np.random.seed(self.random_state)
        self.n_classes_ = len(np.unique(y))
        self.n_features_ = X.shape[1]
        if self.max_features is None:
            self.max_features = self.n_features_  # default: consider all
        self.root = self._grow_tree(X, y, depth=0)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels for *X*.

        Returns
        -------
        y_pred: np.ndarray, shape (n_samples,)
        """
        return np.array([self._traverse_tree(x, self.root) for x in X])

    @property
    def feature_importances_(self) -> np.ndarray:
        """Return normalized feature importances.

        Importance of a feature is the total reduction in Gini impurity it
        contributed across all splits of the tree.
        """
        total = sum(self._feature_importances.values())
        if total == 0:
            return np.zeros(self.n_features_)
        importances = np.zeros(self.n_features_)
        for idx, value in self._feature_importances.items():
            importances[idx] = value / total
        return importances

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _grow_tree(self, X: np.ndarray, y: np.ndarray, depth: int) -> Node:
        n_samples, n_features = X.shape
        node = Node(gini=gini(y), n_samples=n_samples)

        # Stopping criteria
        if (
            depth >= self.max_depth
            or n_samples < self.min_samples_split
            or len(np.unique(y)) == 1
        ):
            node.value = most_common_label(y)
            return node

        # Random subset of features for this split
        feature_idxs = np.random.choice(
            n_features, self.max_features, replace=False
        )

        # Find the best split among selected features
        best_feat, best_thr, best_gain = None, None, -1.0
        for feat_idx in feature_idxs:
            X_column = X[:, feat_idx]
            thresholds = np.unique(X_column)
            # Try each threshold as candidate split point
            for thr in thresholds:
                left_mask = X_column <= thr
                right_mask = X_column > thr
                if (
                    left_mask.sum() < self.min_samples_leaf
                    or right_mask.sum() < self.min_samples_leaf
                ):
                    continue
                y_left, y_right = y[left_mask], y[right_mask]
                gini_left, gini_right = gini(y_left), gini(y_right)
                # Weighted impurity reduction (aka gain)
                gain = node.gini - (
                    left_mask.sum() / n_samples * gini_left
                    + right_mask.sum() / n_samples * gini_right
                )
                if gain > best_gain:
                    best_gain = gain
                    best_feat = feat_idx
                    best_thr = thr

        # If no valid split was found, make leaf
        if best_gain <= 0 or best_feat is None:
            node.value = most_common_label(y)
            return node

        # Record impurity reduction for feature‑importance
        self._feature_importances[best_feat] += best_gain * n_samples

        # Create child nodes recursively
        left_mask = X[:, best_feat] <= best_thr
        right_mask = X[:, best_feat] > best_thr
        node.feature_index = best_feat
        node.threshold = best_thr
        node.left = self._grow_tree(X[left_mask], y[left_mask], depth + 1)
        node.right = self._grow_tree(X[right_mask], y[right_mask], depth + 1)
        return node

    def _traverse_tree(self, x: np.ndarray, node: Node) -> int:
        while not node.is_leaf():
            if x[node.feature_index] <= node.threshold:
                node = node.left  # type: ignore
            else:
                node = node.right  # type: ignore
        return node.value  # type: ignore

# -----------------------------------------------------------------------------
# Random Forest implementation
# -----------------------------------------------------------------------------
class RandomForest:
    """Random Forest classifier built from scratch.

    Parameters
    ----------
    n_estimators: int, default=10
        Number of trees in the forest.
    max_depth: int, default=10
        Maximum depth of each tree.
    min_samples_split: int, default=2
        Minimum samples required to split an internal node.
    min_samples_leaf: int, default=1
        Minimum samples required to be at a leaf node.
    max_features: Optional[int]
        Number of features to consider when looking for the best split. If ``None``
        ``sqrt(num_features)`` is used (standard RF default).
    bootstrap: bool, default=True
        Whether bootstrap samples are used when building trees.
    random_state: Optional[int]
        Seed for reproducibility.
    """

    def __init__(
        self,
        n_estimators: int = 10,
        max_depth: int = 10,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: Optional[int] = None,
        bootstrap: bool = True,
        random_state: Optional[int] = None,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.bootstrap = bootstrap
        self.random_state = random_state
        self.trees_: List[DecisionTree] = []
        self.n_features_: Optional[int] = None
        self._feature_importances: Optional[np.ndarray] = None

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForest":
        if self.random_state is not None:
            np.random.seed(self.random_state)
        self.n_features_ = X.shape[1]
        # default max_features = sqrt(num_features) as in classic RF
        if self.max_features is None:
            self.max_features = int(np.sqrt(self.n_features_))
        self.trees_ = []
        for i in range(self.n_estimators):
            # Bootstrap sample
            if self.bootstrap:
                indices = np.random.choice(
                    X.shape[0], X.shape[0], replace=True
                )
                X_sample, y_sample = X[indices], y[indices]
            else:
                X_sample, y_sample = X, y
            tree = DecisionTree(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                min_samples_leaf=self.min_samples_leaf,
                max_features=self.max_features,
                random_state=self.random_state,
            )
            tree.fit(X_sample, y_sample)
            self.trees_.append(tree)
        # compute aggregated feature importances
        self._aggregate_feature_importances()
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        # collect predictions from each tree
        tree_preds = np.array([tree.predict(X) for tree in self.trees_])
        # majority vote (mode) across axis=0
        majority = []
        for col in tree_preds.T:
            counts = np.bincount(col)
            majority.append(np.argmax(counts))
        return np.array(majority)

    @property
    def feature_importances_(self) -> np.ndarray:
        """Return normalized feature importances for the forest."""
        if self._feature_importances is None:
            self._aggregate_feature_importances()
        return self._feature_importances  # type: ignore

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _aggregate_feature_importances(self) -> None:
        # Sum importances from all trees and normalize
        total_importance = np.zeros(self.n_features_)
        for tree in self.trees_:
            total_importance += tree.feature_importances_
        norm = total_importance.sum()
        if norm == 0:
            self._feature_importances = np.zeros_like(total_importance)
        else:
            self._feature_importances = total_importance / norm

# -----------------------------------------------------------------------------
# Main execution block
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # ---------------------------------------------------------------------
    # 1. Load data
    # ---------------------------------------------------------------------
    data_path = os.path.join("data", "synthetic_data.csv")
    df = pd.read_csv(data_path)

    # ---------------------------------------------------------------------
    # 2. Handle missing values
    # ---------------------------------------------------------------------
    # Numeric columns – fill with median
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    df[num_cols] = df[num_cols].apply(lambda col: col.fillna(col.median()))
    # Categorical columns – fill with mode
    cat_cols = df.select_dtypes(include=[object]).columns.tolist()
    df[cat_cols] = df[cat_cols].apply(lambda col: col.fillna(col.mode()[0]))

    # ---------------------------------------------------------------------
    # 3. Encode categorical variables (skin_type, routine)
    # ---------------------------------------------------------------------
    le_skin = LabelEncoder()
    df["skin_type"] = le_skin.fit_transform(df["skin_type"])
    le_target = LabelEncoder()
    y = le_target.fit_transform(df["routine"])
    X = df.drop(columns=["routine"]).values

    # ---------------------------------------------------------------------
    # 4. Train‑test split
    # ---------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ---------------------------------------------------------------------
    # 5. Train Random Forest
    # ---------------------------------------------------------------------
    rf = RandomForest(
        n_estimators=30,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)

    # ---------------------------------------------------------------------
    # 6. Evaluation
    # ---------------------------------------------------------------------
    # Original evaluation prints removed; results are saved later
    # ---------------------------------------------------------------------
    # 6. Evaluation (extended with result saving)
    # ---------------------------------------------------------------------
    # Compute evaluation metrics
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='macro')
    rec = recall_score(y_test, y_pred, average='macro')
    f1 = f1_score(y_test, y_pred, average='macro')
    cm = confusion_matrix(y_test, y_pred)
    class_report = classification_report(y_test, y_pred, target_names=le_target.classes_)

    # Print to console (unchanged format)
    print("\n--- Evaluation Metrics ---\n")
    print(f"Accuracy : {acc:.4f}")
    print(f"Precision (macro) : {prec:.4f}")
    print(f"Recall (macro)    : {rec:.4f}")
    print(f"F1-score (macro)  : {f1:.4f}\n")
    print("Confusion Matrix:")
    print(cm)
    print("\nClassification Report:")
    print(class_report)

    # -----------------------------------------------------
    # 6a. Save evaluation results to rf_result folder
    # -----------------------------------------------------
    import matplotlib.pyplot as plt

    results_dir = "rf_result"
    os.makedirs(results_dir, exist_ok=True)

    # 6a.1 Save metrics text file
    metrics_path = os.path.join(results_dir, "evaluation_metrics.txt")
    with open(metrics_path, "w") as f:
        f.write("Evaluation Metrics\n")
        f.write(f"Accuracy : {acc:.4f}\n")
        f.write(f"Precision (Macro) : {prec:.4f}\n")
        f.write(f"Recall (Macro)    : {rec:.4f}\n")
        f.write(f"F1-Score (Macro) : {f1:.4f}\n")

    # 6a.2 Save confusion matrix as PNG heatmap
    cm_path = os.path.join(results_dir, "confusion_matrix.png")
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title("Random Forest Confusion Matrix")
    plt.colorbar()
    tick_marks = np.arange(len(le_target.classes_))
    plt.xticks(tick_marks, le_target.classes_, rotation=45)
    plt.yticks(tick_marks, le_target.classes_)
    # Annotate cells
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, format(cm[i, j], "d"),
                     ha="center", va="center",
                     color="white" if cm[i, j] > thresh else "black")
    plt.tight_layout()
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(cm_path, dpi=300, bbox_inches="tight")
    plt.close()

    # 6a.3 Save classification report
    report_path = os.path.join(results_dir, "classification_report.txt")
    with open(report_path, "w") as f:
        f.write(class_report)

    # 6a.4 Save feature importance CSV and plot (handled later after importance is computed)
    # Placeholder – will be saved after feature importance section.

    # 6a.5 Save training summary (will be appended later)
    summary_path = os.path.join(results_dir, "training_summary.txt")
    with open(summary_path, "w") as f:
        f.write("=== Evaluation Metrics ===\n")
        f.write(f"Accuracy : {acc:.4f}\n")
        f.write(f"Precision (Macro) : {prec:.4f}\n")
        f.write(f"Recall (Macro)    : {rec:.4f}\n")
        f.write(f"F1-Score (Macro) : {f1:.4f}\n\n")
        f.write("=== Confusion Matrix ===\n")
        f.write(np.array2string(cm) + "\n\n")
        f.write("=== Classification Report ===\n")
        f.write(class_report + "\n")
        # Feature importance will be appended later.

    # Continue with the rest of the script.
    # ---------------------------------------------------------------------

    # ---------------------------------------------------------------------
    # 7. Feature importance
    # ---------------------------------------------------------------------
    importances = rf.feature_importances_
    feature_names = df.drop(columns=["routine"]).columns.tolist()
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances,
    }).sort_values(by="importance", ascending=False)
    print("\nFeature Importances (normalized):")
    print(importance_df.to_string(index=False))

    # Save feature importance CSV
    fi_csv_path = os.path.join(results_dir, "feature_importance.csv")
    importance_df.to_csv(fi_csv_path, index=False)

    # Save feature importance bar chart
    plt.figure(figsize=(8, 6))
    importance_df.plot.barh(x="feature", y="importance", legend=False)
    plt.title("Random Forest Feature Importances")
    plt.xlabel("Importance")
    plt.gca().invert_yaxis()  # highest at top
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "feature_importance.png"), dpi=300)
    plt.close()

    # Append feature importance to training summary
    with open(summary_path, "a") as f:
        f.write("=== Feature Importances ===\n")
        f.write(importance_df.to_string(index=False) + "\n\n")

    # ---------------------------------------------------------------------
    # 8. Save model
    # ---------------------------------------------------------------------
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "acne_detection_rf.pkl")
    
    skin_map = {str(cls): int(idx) for idx, cls in enumerate(le_skin.classes_)}
    
    with open(model_path, "wb") as f:
        pickle.dump(
            {
                "model": rf,
                "le_skin": le_skin,
                "le_target": le_target,
                "skin_map": skin_map,
                "feature_cols": feature_names,
            },
            f,
        )
    print(f"\nModel successfully saved to {model_path}")

    # ---------------------------------------------------------------------
    # 9. Final result summary printout
    # ---------------------------------------------------------------------
    print("\nResults saved successfully.\n")
    print(
        "rf_result/\n"
        "  evaluation_metrics.txt\n"
        "  classification_report.txt\n"
        "  confusion_matrix.png\n"
        "  feature_importance.csv\n"
        "  feature_importance.png\n"
        "  training_summary.txt"
    )
