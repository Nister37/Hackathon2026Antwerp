"""LifeLine ML study for the hackathon transaction datasets.

Run from the repository root:
    python ml/ml_study.py

The script creates:
    hackathon/output/ml_report.md
    hackathon/output/*.csv
    hackathon/output/*.png

It uses the course ML concepts in an honest way for this tiny synthetic
dataset: feature engineering, explainable classification scores, recurrence
detection, unsupervised clustering, and simple spend forecasting.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt

    PLOTS_AVAILABLE = True
except ImportError:
    plt = None
    PLOTS_AVAILABLE = False

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

try:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("TRANSACTIONS_DIR", BASE_DIR.parent / "data"))
OUTPUT_DIR = Path(os.environ.get("ML_OUTPUT_DIR", BASE_DIR / "output"))
SOURCE_FILES = {"TOM": "tom_transactions.csv", "MARIA": "maria_transactions.csv"}

REQUIRED_CATEGORIES = [
    "Income",
    "Home",
    "Housing",
    "Utilities",
    "Groceries",
    "Travel",
    "Foreign Spend",
    "Other",
]

EVENT_WEIGHTS = {
    "moving_renovation": {
        "geo_drift": 0.25,
        "home_cluster": 0.25,
        "housing_setup": 0.20,
        "velocity_change": 0.15,
        "new_recurring": 0.15,
    },
    "travel_prep": {
        "travel_cluster": 0.30,
        "foreign_spend_signal": 0.25,
        "travel_geo": 0.15,
        "discretionary_drop": 0.15,
        "new_recurring": 0.15,
    },
}


def load_transactions() -> pd.DataFrame:
    frames = []
    for customer, filename in SOURCE_FILES.items():
        file = DATA_DIR / filename
        frame = pd.read_csv(file, parse_dates=["date"])
        if frame.empty or frame["customer_id"].nunique() != 1 or frame["customer_id"].iat[0] != customer:
            raise ValueError(f"Unexpected customer data in {filename}")
        frame["source_file"] = file.name
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df["category"] = pd.Categorical(
        df["category"], categories=REQUIRED_CATEGORIES, ordered=False
    )
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["spend"] = df["amount"].clip(upper=0).abs()
    df["income"] = df["amount"].clip(lower=0)
    df["is_outflow"] = df["amount"] < 0
    return df.sort_values(["customer_id", "date", "transaction_id"]).reset_index(drop=True)


def spend_by_category(df: pd.DataFrame) -> pd.DataFrame:
    pivot = pd.pivot_table(
        df,
        values="spend",
        index="customer_id",
        columns="category",
        aggfunc="sum",
        fill_value=0,
        observed=False,
    )
    return pivot.reindex(columns=REQUIRED_CATEGORIES, fill_value=0).round(2)


def monthly_category_spend(df: pd.DataFrame) -> pd.DataFrame:
    monthly = pd.pivot_table(
        df,
        values="spend",
        index=["customer_id", "month"],
        columns="category",
        aggfunc="sum",
        fill_value=0,
        observed=False,
    )
    return monthly.reindex(columns=REQUIRED_CATEGORIES, fill_value=0).reset_index()


def city_drift_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for customer, group in df.groupby("customer_id"):
        start = group["date"].min()
        end = group["date"].max()
        midpoint = start + (end - start) / 2
        early = group[group["date"] <= midpoint]
        late = group[group["date"] > midpoint]
        for city in sorted(group["city"].dropna().unique()):
            early_share = (early["city"] == city).mean() if len(early) else 0
            late_share = (late["city"] == city).mean() if len(late) else 0
            rows.append(
                {
                    "customer_id": customer,
                    "city": city,
                    "early_share": round(float(early_share), 3),
                    "late_share": round(float(late_share), 3),
                    "share_change": round(float(late_share - early_share), 3),
                }
            )
    return pd.DataFrame(rows)


def cooccurrence_table(df: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    rows = []
    for customer, group in df[df["is_outflow"]].groupby("customer_id"):
        group = group.sort_values("date")
        merchant_category = (
            group.groupby("merchant")["category"]
            .agg(lambda values: values.mode().iat[0])
            .to_dict()
        )
        counter: Counter[tuple[str, str]] = Counter()
        for _, transaction in group.iterrows():
            window_start = transaction["date"]
            window_end = window_start + pd.Timedelta(days=window_days)
            merchants = sorted(
                group.loc[
                    (group["date"] >= window_start) & (group["date"] <= window_end),
                    "merchant",
                ].unique()
            )
            for left, right in combinations(merchants, 2):
                counter[(left, right)] += 1

        for (left, right), count in counter.most_common(100):
            rows.append(
                {
                    "customer_id": customer,
                    "merchant_a": left,
                    "merchant_a_category": merchant_category.get(left, "Other"),
                    "merchant_b": right,
                    "merchant_b_category": merchant_category.get(right, "Other"),
                    "cooccurrence_count": count,
                }
            )
    return pd.DataFrame(rows)


def recurring_transactions(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (customer, merchant), group in df[df["is_outflow"]].groupby(
        ["customer_id", "merchant"]
    ):
        group = group.sort_values("date")
        if len(group) < 3:
            continue
        intervals = group["date"].diff().dt.days.dropna()
        if intervals.empty:
            continue
        median_interval = float(intervals.median())
        interval_std = float(intervals.std(ddof=0))
        mean_amount = float(group["spend"].mean())
        amount_cv = float(group["spend"].std(ddof=0) / mean_amount) if mean_amount else 0
        looks_monthly = 25 <= median_interval <= 35 and interval_std <= 5
        amount_is_stable = amount_cv <= 0.15
        if looks_monthly and amount_is_stable:
            rows.append(
                {
                    "customer_id": customer,
                    "merchant": merchant,
                    "category": group["category"].mode().iat[0],
                    "occurrences": len(group),
                    "median_interval_days": round(median_interval, 1),
                    "interval_std_days": round(interval_std, 1),
                    "amount_cv": round(amount_cv, 3),
                    "first_seen": group["date"].min().date().isoformat(),
                    "last_seen": group["date"].max().date().isoformat(),
                    "typical_amount": round(float(group["spend"].median()), 2),
                }
            )
    return pd.DataFrame(rows)


def _category_recent_baseline(group: pd.DataFrame, latest: pd.Timestamp) -> pd.DataFrame:
    recent_start = latest - pd.Timedelta(days=60)
    baseline = group[group["date"] < recent_start]
    recent = group[group["date"] >= recent_start]

    baseline_days = max((recent_start - group["date"].min()).days, 1)
    recent_days = max((latest - recent_start).days + 1, 1)

    rows = []
    for category in REQUIRED_CATEGORIES:
        base_total = baseline.loc[baseline["category"] == category, "spend"].sum()
        recent_total = recent.loc[recent["category"] == category, "spend"].sum()
        base_daily = base_total / baseline_days
        recent_daily = recent_total / recent_days
        if base_daily == 0 and recent_daily > 0:
            shift = np.inf
        elif base_daily == 0:
            shift = 0
        else:
            shift = (recent_daily - base_daily) / base_daily
        rows.append(
            {
                "category": category,
                "baseline_spend": round(float(base_total), 2),
                "recent_spend": round(float(recent_total), 2),
                "baseline_daily": round(float(base_daily), 2),
                "recent_daily": round(float(recent_daily), 2),
                "velocity_shift": shift,
            }
        )
    return pd.DataFrame(rows)


def engineer_customer_features(
    df: pd.DataFrame, recurring: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    feature_rows = []
    velocity_tables: dict[str, pd.DataFrame] = {}

    for customer, group in df.groupby("customer_id"):
        latest = group["date"].max()
        recent_start = latest - pd.Timedelta(days=60)
        recent = group[group["date"] >= recent_start]
        baseline = group[group["date"] < recent_start]
        velocity = _category_recent_baseline(group, latest)
        velocity_tables[customer] = velocity

        spend = group["spend"].sum()
        income = group["income"].sum()
        category_totals = group.groupby("category", observed=False)["spend"].sum()
        recent_category = recent.groupby("category", observed=False)["spend"].sum()
        baseline_category = baseline.groupby("category", observed=False)["spend"].sum()

        city_drift = city_drift_table(group)
        geo_drift = float(city_drift["share_change"].abs().max()) if len(city_drift) else 0
        foreign_tx = int((group["category"] == "Foreign Spend").sum())
        non_be_tx = int((group["country"] != "BE").sum())

        recent_home_merchants = recent.loc[
            recent["category"] == "Home", "merchant"
        ].nunique()
        recent_travel_merchants = recent.loc[
            recent["category"] == "Travel", "merchant"
        ].nunique()

        home_baseline = baseline_category.get("Home", 0.0)
        home_recent = recent_category.get("Home", 0.0)
        travel_recent = recent_category.get("Travel", 0.0)
        foreign_recent = recent_category.get("Foreign Spend", 0.0)

        home_cluster = min(1.0, recent_home_merchants / 4) * (
            1.0 if home_recent > home_baseline else 0.5
        )
        housing_setup = min(
            1.0,
            (
                int(group["merchant"].str.contains("Notary|Moving|Mortgage", case=False).sum())
                + int(recent_category.get("Utilities", 0.0) > baseline_category.get("Utilities", 0.0))
            )
            / 4,
        )
        travel_cluster = min(1.0, recent_travel_merchants / 4)
        foreign_spend = min(1.0, foreign_tx / 3)
        travel_geo = min(1.0, non_be_tx / 2)

        other_velocity = velocity.loc[velocity["category"] == "Other", "velocity_shift"].iat[0]
        discretionary_drop = min(1.0, max(0.0, -float(other_velocity)))
        max_shift = velocity["velocity_shift"].replace([np.inf, -np.inf], np.nan).abs().max()
        velocity_change = min(1.0, float(max_shift) / 2) if pd.notna(max_shift) else 1.0

        if recurring.empty:
            customer_recurring = pd.DataFrame()
        else:
            customer_recurring = recurring[recurring["customer_id"] == customer].copy()
        new_recurring = 0
        if len(customer_recurring):
            customer_recurring["first_seen_date"] = pd.to_datetime(
                customer_recurring["first_seen"]
            )
            new_recurring = int((customer_recurring["first_seen_date"] >= recent_start).sum())

        feature_rows.append(
            {
                "customer_id": customer,
                "transactions": len(group),
                "income_total": round(float(income), 2),
                "spend_total": round(float(spend), 2),
                "surplus_total": round(float(income - spend), 2),
                "home_spend": round(float(category_totals.get("Home", 0.0)), 2),
                "housing_spend": round(float(category_totals.get("Housing", 0.0)), 2),
                "travel_spend": round(float(category_totals.get("Travel", 0.0)), 2),
                "foreign_spend_total": round(
                    float(category_totals.get("Foreign Spend", 0.0)), 2
                ),
                "geo_drift": round(geo_drift, 3),
                "home_cluster": round(home_cluster, 3),
                "housing_setup": round(housing_setup, 3),
                "velocity_change": round(velocity_change, 3),
                "new_recurring": min(1.0, new_recurring / 2),
                "travel_cluster": round(travel_cluster, 3),
                "foreign_spend_signal": round(foreign_spend, 3),
                "travel_geo": round(travel_geo, 3),
                "discretionary_drop": round(discretionary_drop, 3),
                "home_merchants_recent": recent_home_merchants,
                "travel_merchants_recent": recent_travel_merchants,
                "foreign_tx_count": foreign_tx,
                "non_be_tx_count": non_be_tx,
            }
        )

    return pd.DataFrame(feature_rows), velocity_tables


def classify_life_events(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in features.iterrows():
        scores: dict[str, float] = {}
        for event, weights in EVENT_WEIGHTS.items():
            score = 0.0
            for signal, weight in weights.items():
                score += float(row[signal]) * weight
            scores[event] = min(score / sum(weights.values()), 1.0)

        best_event = max(scores, key=scores.get)
        rows.append(
            {
                "customer_id": row["customer_id"],
                "moving_renovation_score": round(scores["moving_renovation"], 3),
                "travel_prep_score": round(scores["travel_prep"], 3),
                "predicted_event": best_event,
                "confidence_percent": round(scores[best_event] * 100, 1),
            }
        )
    return pd.DataFrame(rows)


def monthly_model_table(df: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly_category_spend(df)
    grouped = (
        df.groupby(["customer_id", "month"])
        .agg(
            total_spend=("spend", "sum"),
            income=("income", "sum"),
            unique_merchants=("merchant", "nunique"),
            unique_cities=("city", "nunique"),
            foreign_tx=("country", lambda s: int((s != "BE").sum())),
        )
        .reset_index()
    )
    merged = grouped.merge(monthly, on=["customer_id", "month"], how="left")
    return merged.sort_values(["customer_id", "month"])


def cluster_months(monthly: pd.DataFrame) -> pd.DataFrame:
    feature_columns = REQUIRED_CATEGORIES + [
        "total_spend",
        "unique_merchants",
        "unique_cities",
        "foreign_tx",
    ]
    result = monthly.copy()
    if len(result) < 2:
        result["cluster"] = 0
        result["cluster_x"] = 0.0
        result["cluster_y"] = 0.0
        return result

    x = result[feature_columns].fillna(0).astype(float)
    if SKLEARN_AVAILABLE:
        model = make_pipeline(StandardScaler(), KMeans(n_clusters=2, random_state=42, n_init=10))
        result["cluster"] = model.fit_predict(x)
        coords = PCA(n_components=2, random_state=42).fit_transform(StandardScaler().fit_transform(x))
        result["cluster_x"] = coords[:, 0]
        result["cluster_y"] = coords[:, 1]
    else:
        threshold = x["Travel"].add(x["Foreign Spend"]).add(x["Home"]).median()
        result["cluster"] = (x["Travel"] + x["Foreign Spend"] + x["Home"] > threshold).astype(int)
        result["cluster_x"] = x["Home"] - x["Travel"]
        result["cluster_y"] = x["Foreign Spend"] + x["Travel"]
    return result


def forecast_spend(monthly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for customer, group in monthly.groupby("customer_id"):
        group = group.sort_values("month").reset_index(drop=True)
        y = group["total_spend"].astype(float).to_numpy()
        x_next = len(group)
        if SKLEARN_AVAILABLE and len(group) >= 3:
            x = np.arange(len(group)).reshape(-1, 1)
            model = LinearRegression()
            model.fit(x, y)
            next_month = float(model.predict(np.array([[x_next]]))[0])
            method = "LinearRegression(month_index -> total_spend)"
        else:
            next_month = float(pd.Series(y).tail(3).mean())
            method = "3-month moving average"

        recent_std = float(pd.Series(y).tail(3).std(ddof=0))
        rows.append(
            {
                "customer_id": customer,
                "next_month_spend_forecast": round(max(next_month, 0.0), 2),
                "next_90_days_forecast": round(max(next_month, 0.0) * 3, 2),
                "uncertainty_band_plus_minus": round(recent_std * 3, 2),
                "method": method,
            }
        )
    return pd.DataFrame(rows)


def label_window(customer: str, window: pd.DataFrame, end_date: pd.Timestamp) -> str:
    """Create demo labels from the known mock-persona scenario.

    In a real bank, these labels would come from consented customer feedback,
    product journeys, or manually reviewed historical cases. For the hackathon
    CSVs, we use the scenario design to create a small supervised dataset.
    """
    category_spend = window.groupby("category", observed=False)["spend"].sum()
    cities = window["city"].value_counts(normalize=True)
    merchants = window["merchant"].str.lower()

    if customer == "MARIA":
        has_home_activity = category_spend.get("Home", 0.0) >= 150
        has_moving_signal = merchants.str.contains("notary|moving|mortgage").any()
        ghent_share = float(cities.get("Ghent", 0.0))
        if end_date >= pd.Timestamp("2026-06-01") and (
            has_home_activity or has_moving_signal or ghent_share >= 0.35
        ):
            return "moving_renovation"

    if customer == "TOM":
        has_travel_activity = (
            category_spend.get("Travel", 0.0) > 0
            or category_spend.get("Foreign Spend", 0.0) > 0
            or (window["country"] != "BE").any()
        )
        if end_date >= pd.Timestamp("2026-06-01") and has_travel_activity:
            return "travel_prep"

    return "normal"


def build_window_training_set(
    df: pd.DataFrame, window_days: int = 45, step_days: int = 7
) -> tuple[pd.DataFrame, list[str]]:
    rows = []
    cities = sorted(df["city"].dropna().unique())

    for customer, group in df.groupby("customer_id"):
        group = group.sort_values("date")
        first_end = group["date"].min() + pd.Timedelta(days=window_days - 1)
        last_end = group["date"].max()
        for end_date in pd.date_range(first_end, last_end, freq=f"{step_days}D"):
            start_date = end_date - pd.Timedelta(days=window_days - 1)
            window = group[(group["date"] >= start_date) & (group["date"] <= end_date)]
            if len(window) < 5:
                continue

            outflow = window[window["is_outflow"]]
            category_spend = outflow.groupby("category", observed=False)["spend"].sum()
            category_count = outflow.groupby("category", observed=False).size()
            city_share = window["city"].value_counts(normalize=True)
            merchant_text = window["merchant"].str.lower()

            total_income = float(window["income"].sum())
            total_spend = float(window["spend"].sum())
            row = {
                "customer_id": customer,
                "window_start": start_date.date().isoformat(),
                "window_end": end_date.date().isoformat(),
                "label": label_window(customer, window, end_date),
                "total_income": total_income,
                "total_spend": total_spend,
                "surplus": total_income - total_spend,
                "outflow_tx_count": int(len(outflow)),
                "unique_merchants": int(outflow["merchant"].nunique()),
                "unique_cities": int(window["city"].nunique()),
                "non_be_tx_count": int((window["country"] != "BE").sum()),
                "home_merchant_count": int(
                    outflow.loc[outflow["category"] == "Home", "merchant"].nunique()
                ),
                "travel_merchant_count": int(
                    outflow.loc[outflow["category"] == "Travel", "merchant"].nunique()
                ),
                "moving_keyword_count": int(
                    merchant_text.str.contains("notary|moving|mortgage").sum()
                ),
                "fx_keyword_count": int(merchant_text.str.contains("fx|eur-jpy").sum()),
            }

            for category in REQUIRED_CATEGORIES:
                safe_name = category.lower().replace(" ", "_")
                row[f"spend_{safe_name}"] = float(category_spend.get(category, 0.0))
                row[f"count_{safe_name}"] = int(category_count.get(category, 0))

            for city in cities:
                row[f"city_share_{city.lower()}"] = float(city_share.get(city, 0.0))

            rows.append(row)

    samples = pd.DataFrame(rows)
    feature_columns = [
        column
        for column in samples.columns
        if column not in {"customer_id", "window_start", "window_end", "label"}
    ]
    return samples, feature_columns


def train_life_event_model(
    samples: pd.DataFrame, feature_columns: list[str]
) -> dict[str, pd.DataFrame | str | float | None]:
    if not SKLEARN_AVAILABLE:
        return {
            "status": "sklearn is not available, so the trained classifier was skipped.",
            "accuracy": None,
            "report": pd.DataFrame(),
            "confusion": pd.DataFrame(),
            "feature_importance": pd.DataFrame(),
            "latest_predictions": pd.DataFrame(),
        }

    class_counts = samples["label"].value_counts()
    if len(class_counts) < 2 or class_counts.min() < 2:
        return {
            "status": "Not enough labelled windows per class to train/test a classifier.",
            "accuracy": None,
            "report": pd.DataFrame(),
            "confusion": pd.DataFrame(),
            "feature_importance": pd.DataFrame(),
            "latest_predictions": pd.DataFrame(),
        }

    x = samples[feature_columns].fillna(0).astype(float)
    y = samples["label"]
    stratify = y if class_counts.min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.35,
        random_state=42,
        stratify=stratify,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)

    labels = sorted(y.unique())
    report = pd.DataFrame(
        classification_report(
            y_test,
            y_pred,
            labels=labels,
            output_dict=True,
            zero_division=0,
        )
    ).T.reset_index(names="label")
    confusion = pd.DataFrame(
        confusion_matrix(y_test, y_pred, labels=labels),
        index=[f"actual_{label}" for label in labels],
        columns=[f"pred_{label}" for label in labels],
    )
    confusion.index.name = "actual_label"
    importance = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    latest_indices = samples.groupby("customer_id")["window_end"].idxmax()
    latest = samples.loc[latest_indices].copy()
    probabilities = model.predict_proba(latest[feature_columns].fillna(0).astype(float))
    pred_labels = model.classes_[np.argmax(probabilities, axis=1)]
    latest["model_prediction"] = pred_labels
    latest["model_confidence_percent"] = np.max(probabilities, axis=1) * 100
    for index, class_name in enumerate(model.classes_):
        latest[f"prob_{class_name}"] = probabilities[:, index]

    return {
        "status": "RandomForestClassifier trained on rolling transaction windows.",
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "report": report.round(3),
        "confusion": confusion,
        "feature_importance": importance.head(20).reset_index(drop=True).round(4),
        "latest_predictions": latest[
            [
                "customer_id",
                "window_start",
                "window_end",
                "label",
                "model_prediction",
                "model_confidence_percent",
            ]
            + [column for column in latest.columns if column.startswith("prob_")]
        ].reset_index(drop=True).round(3),
    }


def answer_business_questions(
    scores: pd.DataFrame, features: pd.DataFrame, model_results: dict[str, Any]
) -> list[str]:
    latest_model = model_results.get("latest_predictions")
    lines = [
        "## Business Questions Answered",
        "",
        "### Can KBC detect needs before the customer interacts?",
        "",
        "Yes for this proof of concept. The transaction history contains early signals before an explicit request: Maria's geography and home spend shift toward a move/renovation pattern, while Tom's travel and FX transactions reveal trip preparation.",
        "",
        "### What should KBC detect?",
        "",
        "- Maria: moving/renovation need, with support around renovation budgeting, utilities, home insurance, and cash-flow pressure.",
        "- Tom: travel preparation need, with support around exchange rates, travel card fees, insurance, and daily trip budget.",
        "",
        "### How confident is the system?",
        "",
    ]

    for _, row in scores.iterrows():
        readable = (
            "moving/renovation"
            if row["predicted_event"] == "moving_renovation"
            else "travel preparation"
        )
        lines.append(
            f"- {row['customer_id']}: explainable score predicts {readable} at {row['confidence_percent']:.1f}%."
        )

    if isinstance(latest_model, pd.DataFrame) and len(latest_model):
        lines.extend(["", "The trained classifier's latest-window predictions are:"])
        for _, row in latest_model.iterrows():
            lines.append(
                f"- {row['customer_id']}: model predicts {row['model_prediction']} at {row['model_confidence_percent']:.1f}%."
            )

    lines.extend(
        [
            "",
            "### What makes this useful for KBC?",
            "",
            "The output is not just a class label. It gives the bank a reason, a confidence level, and one next-best action. That is the difference between intrusive targeting and useful proactive support.",
            "",
            "### What would be needed in production?",
            "",
            "KBC would need many more consented and labelled customer histories, strict privacy controls, train/test validation by time and customer, fairness checks, monitoring for drift, and an opt-in explanation layer before using inferences for commercial actions.",
            "",
        ]
    )
    return lines


def _currency(value: float) -> str:
    return f"EUR {float(value):,.2f}"


def _score_level(confidence: float) -> str:
    if confidence >= 75:
        return "high"
    if confidence >= 55:
        return "medium"
    return "low"


def _event_relevant_merchant_pairs(
    pairs: pd.DataFrame, event: str
) -> list[dict[str, Any]]:
    if pairs.empty:
        return []

    if event == "moving_renovation":
        categories = {"Home", "Housing", "Utilities"}
    else:
        categories = {"Travel", "Foreign Spend"}

    relevant = pairs[
        pairs["merchant_a_category"].isin(categories)
        | pairs["merchant_b_category"].isin(categories)
    ]
    if relevant.empty:
        relevant = pairs

    return (
        relevant[
            [
                "merchant_a",
                "merchant_a_category",
                "merchant_b",
                "merchant_b_category",
                "cooccurrence_count",
            ]
        ]
        .head(3)
        .to_dict(orient="records")
    )


def generate_profile_suggestions(
    features: pd.DataFrame,
    scores: pd.DataFrame,
    forecasts: pd.DataFrame,
    recurring: pd.DataFrame,
    city_drift: pd.DataFrame,
    cooccurrence: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Create app-facing cards from model outputs.

    The frontend should render this JSON, not the raw model feature table. Each
    card keeps the signal explainable by carrying the numbers that caused it.
    """
    suggestions: list[dict[str, Any]] = []

    for _, score_row in scores.iterrows():
        customer = str(score_row["customer_id"])
        event = str(score_row["predicted_event"])
        confidence = float(score_row["confidence_percent"])
        feature = features[features["customer_id"] == customer].iloc[0]
        forecast = forecasts[forecasts["customer_id"] == customer].iloc[0]
        customer_city_drift = city_drift[city_drift["customer_id"] == customer]
        customer_recurring = (
            recurring[recurring["customer_id"] == customer]
            if len(recurring)
            else pd.DataFrame()
        )
        customer_cooccurrence = (
            cooccurrence[cooccurrence["customer_id"] == customer]
            if len(cooccurrence)
            else pd.DataFrame()
        )

        base_card: dict[str, Any] = {
            "id": f"{customer.lower()}-{event}",
            "customer_id": customer,
            "event": event,
            "confidence_percent": round(confidence, 1),
            "confidence_level": _score_level(confidence),
            "forecast": {
                "next_90_days_spend": float(forecast["next_90_days_forecast"]),
                "uncertainty_band_plus_minus": float(
                    forecast["uncertainty_band_plus_minus"]
                ),
                "display": (
                    f"Next 90 days around "
                    f"{_currency(forecast['next_90_days_forecast'])}"
                ),
            },
            "money_mirror": {
                "income_total": float(feature["income_total"]),
                "spend_total": float(feature["spend_total"]),
                "surplus_total": float(feature["surplus_total"]),
                "display": (
                    f"Income {_currency(feature['income_total'])}, "
                    f"spend {_currency(feature['spend_total'])}, "
                    f"surplus {_currency(feature['surplus_total'])}"
                ),
            },
            "source": {
                "model": "weighted_signal_classifier",
                "files": ["features.csv", "classification_scores.csv", "spend_forecast.csv"],
            },
        }

        if event == "moving_renovation":
            evidence = [
                {
                    "label": "Home spending",
                    "value": float(feature["home_spend"]),
                    "display": f"Home spend is {_currency(feature['home_spend'])}",
                },
                {
                    "label": "Location shift",
                    "value": float(feature["geo_drift"]),
                    "display": (
                        "Spending location changed strongly between the early "
                        "and recent transaction history"
                    ),
                },
                {
                    "label": "Housing setup",
                    "value": float(feature["housing_setup"]),
                    "display": "Housing setup signals include notary, moving, or mortgage activity",
                },
            ]
            actions = [
                {
                    "id": "track-renovation-spend",
                    "label": "Track renovation spending",
                    "impact": f"Group {_currency(feature['home_spend'])} of home expenses",
                    "kind": "dashboard",
                },
                {
                    "id": "review-home-cashflow",
                    "label": "Review home cash flow",
                    "impact": base_card["forecast"]["display"],
                    "kind": "money_mirror",
                },
            ]
            base_card.update(
                {
                    "title": "Possible home pattern",
                    "summary": (
                        "Your transactions may suggest a move or renovation pattern."
                    ),
                    "body": (
                        "We noticed home-related spending, housing setup payments, "
                        "and a strong change in where day-to-day spending happens."
                    ),
                    "primary_action_id": "track-renovation-spend",
                    "evidence": evidence,
                    "actions": actions,
                    "ui_route": f"/profile/{customer.lower()}/lifeline/home",
                }
            )
        else:
            evidence = [
                {
                    "label": "Travel spending",
                    "value": float(feature["travel_spend"]),
                    "display": f"Travel spend is {_currency(feature['travel_spend'])}",
                },
                {
                    "label": "Foreign spend",
                    "value": float(feature["foreign_spend_total"]),
                    "display": (
                        f"Foreign exchange or foreign spend is "
                        f"{_currency(feature['foreign_spend_total'])}"
                    ),
                },
                {
                    "label": "Foreign transactions",
                    "value": int(feature["foreign_tx_count"]),
                    "display": f"{int(feature['foreign_tx_count'])} foreign spend transactions detected",
                },
            ]
            actions = [
                {
                    "id": "set-trip-budget",
                    "label": "Set trip budget",
                    "impact": base_card["forecast"]["display"],
                    "kind": "budget",
                },
                {
                    "id": "review-fx-fees",
                    "label": "Review FX fees",
                    "impact": f"Check {_currency(feature['foreign_spend_total'])} of foreign spend",
                    "kind": "fees",
                },
            ]
            base_card.update(
                {
                    "title": "Possible travel pattern",
                    "summary": "Your transactions may suggest upcoming travel preparation.",
                    "body": (
                        "We noticed travel merchants, foreign exchange activity, "
                        "and a change in discretionary spending."
                    ),
                    "primary_action_id": "set-trip-budget",
                    "evidence": evidence,
                    "actions": actions,
                    "ui_route": f"/profile/{customer.lower()}/lifeline/travel",
                }
            )

        if len(customer_city_drift):
            strongest_city = customer_city_drift.iloc[
                customer_city_drift["share_change"].abs().argmax()
            ]
            base_card["strongest_city_change"] = {
                "city": str(strongest_city["city"]),
                "early_share": float(strongest_city["early_share"]),
                "late_share": float(strongest_city["late_share"]),
                "share_change": float(strongest_city["share_change"]),
            }

        if len(customer_recurring):
            base_card["recurring_merchants"] = (
                customer_recurring.sort_values("typical_amount", ascending=False)[
                    ["merchant", "category", "typical_amount"]
                ]
                .head(3)
                .to_dict(orient="records")
            )
        else:
            base_card["recurring_merchants"] = []

        base_card["merchant_pairs"] = _event_relevant_merchant_pairs(
            customer_cooccurrence, event
        )

        suggestions.append(base_card)

    return suggestions


def profile_artifact(suggestions: list[dict[str, Any]]) -> dict[str, Any]:
    """Bind the explainable cards to the exact CSV snapshot they were derived from."""
    if len(suggestions) != len(SOURCE_FILES) or Counter(
        card["customer_id"] for card in suggestions
    ) != Counter(SOURCE_FILES.keys()):
        raise ValueError("Expected one suggestion for each demo customer")
    return {
        "schema_version": 1,
        "source_sha256": {
            filename: sha256((DATA_DIR / filename).read_bytes()).hexdigest()
            for filename in SOURCE_FILES.values()
        },
        "suggestions": suggestions,
    }


def write_profile_artifact(suggestions: list[dict[str, Any]], directory: Path = OUTPUT_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "profile_suggestions.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(profile_artifact(suggestions), indent=2), encoding="utf-8")
    temporary.replace(destination)
    return destination


def write_plots(
    df: pd.DataFrame,
    category: pd.DataFrame,
    monthly: pd.DataFrame,
    clustered: pd.DataFrame,
) -> None:
    if not PLOTS_AVAILABLE:
        print("matplotlib is not available; skipping PNG chart outputs.")
        return

    plt.style.use("default")

    category_plot = category.drop(columns=["Income"], errors="ignore")
    ax = category_plot.T.plot(kind="bar", figsize=(12, 6))
    ax.set_title("Total outflow by category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Spend (EUR)")
    ax.legend(title="Customer")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "category_spend.png", dpi=160)
    plt.close()

    total_monthly = (
        df.groupby(["customer_id", "month"])["spend"].sum().reset_index()
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    for customer, group in total_monthly.groupby("customer_id"):
        ax.plot(group["month"], group["spend"], marker="o", label=customer)
    ax.set_title("Monthly total outflow")
    ax.set_xlabel("Month")
    ax.set_ylabel("Spend (EUR)")
    ax.legend()
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "monthly_spend.png", dpi=160)
    plt.close()

    city_counts = (
        df[df["is_outflow"]]
        .groupby(["customer_id", "month", "city"])
        .size()
        .reset_index(name="transactions")
    )
    for customer, group in city_counts.groupby("customer_id"):
        pivot = group.pivot_table(
            index="month", columns="city", values="transactions", fill_value=0
        )
        ax = pivot.plot(kind="bar", stacked=True, figsize=(10, 5))
        ax.set_title(f"{customer}: city mix over time")
        ax.set_xlabel("Month")
        ax.set_ylabel("Outflow transactions")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / f"{customer.lower()}_city_mix.png", dpi=160)
        plt.close()

    fig, ax = plt.subplots(figsize=(8, 5))
    for cluster_id, group in clustered.groupby("cluster"):
        ax.scatter(group["cluster_x"], group["cluster_y"], label=f"Cluster {cluster_id}", s=80)
        for _, row in group.iterrows():
            ax.annotate(
                f"{row['customer_id']} {row['month']}",
                (row["cluster_x"], row["cluster_y"]),
                fontsize=8,
                xytext=(4, 4),
                textcoords="offset points",
            )
    ax.set_title("Unsupervised monthly behavior clusters")
    ax.set_xlabel("Component 1")
    ax.set_ylabel("Component 2")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "monthly_clusters.png", dpi=160)
    plt.close()


def markdown_table(frame: pd.DataFrame) -> str:
    """Return a GitHub-style Markdown table without optional dependencies."""
    if isinstance(frame.index, pd.RangeIndex) and frame.index.name is None:
        table = frame.copy()
    else:
        table = frame.reset_index()
    table = table.copy()
    for column in table.columns:
        if pd.api.types.is_datetime64_any_dtype(table[column]):
            table[column] = table[column].dt.strftime("%Y-%m-%d")
    table = table.astype(str)

    headers = list(table.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in headers) + " |")
    return "\n".join(lines)


def explain_customer(
    customer: str,
    features: pd.Series,
    scores: pd.Series,
    forecast: pd.Series,
    velocity: pd.DataFrame,
    recurring: pd.DataFrame,
    city_drift: pd.DataFrame,
    cooccurrence: pd.DataFrame,
) -> list[str]:
    event = str(scores["predicted_event"])
    confidence = float(scores["confidence_percent"])
    event_label = "Moving / renovation" if event == "moving_renovation" else "Travel prep"
    lines = [f"### {customer}: {event_label}", ""]
    lines.append(f"- Predicted event: **{event_label}** with **{confidence:.1f}%** confidence.")
    lines.append(
        f"- Total income: EUR {features['income_total']:,.2f}; total spend: EUR {features['spend_total']:,.2f}; surplus: EUR {features['surplus_total']:,.2f}."
    )
    lines.append(
        f"- Forecast next 90 days: about EUR {forecast['next_90_days_forecast']:,.2f} +/- EUR {forecast['uncertainty_band_plus_minus']:,.2f}."
    )

    if event == "moving_renovation":
        lines.extend(
            [
                f"- Strongest signals: geo drift {features['geo_drift']}, home cluster {features['home_cluster']}, housing setup {features['housing_setup']}.",
                f"- Recent home merchants: {int(features['home_merchants_recent'])}; total home spend: EUR {features['home_spend']:,.2f}.",
            ]
        )
    else:
        lines.extend(
            [
                f"- Strongest signals: travel cluster {features['travel_cluster']}, FX/foreign spend {features['foreign_spend_signal']}, travel geography {features['travel_geo']}.",
                f"- Travel spend: EUR {features['travel_spend']:,.2f}; foreign spend: EUR {features['foreign_spend_total']:,.2f}; foreign transactions: {int(features['foreign_tx_count'])}.",
            ]
        )

    top_velocity = velocity.copy()
    top_velocity["velocity_shift_clean"] = top_velocity["velocity_shift"].replace(
        [np.inf, -np.inf], np.nan
    )
    top_velocity = top_velocity.sort_values("recent_spend", ascending=False).head(3)
    lines.append("- Most important recent category spend:")
    for _, row in top_velocity.iterrows():
        lines.append(
            f"  - {row['category']}: EUR {row['recent_spend']:,.2f} in the recent 60-day window."
        )

    c_drift = city_drift[city_drift["customer_id"] == customer].sort_values(
        "share_change", ascending=False
    )
    if len(c_drift):
        top_city = c_drift.iloc[0]
        lines.append(
            f"- Biggest city change: {top_city['city']} moved from {top_city['early_share']:.0%} to {top_city['late_share']:.0%} of transactions."
        )

    rec = recurring[recurring["customer_id"] == customer] if len(recurring) else pd.DataFrame()
    if len(rec):
        names = ", ".join(rec.sort_values("typical_amount", ascending=False)["merchant"].head(3))
        lines.append(f"- Recurring charges detected: {names}.")

    co = cooccurrence[cooccurrence["customer_id"] == customer] if len(cooccurrence) else pd.DataFrame()
    if len(co):
        if event == "moving_renovation":
            primary_categories = {"Home", "Housing"}
            fallback_categories = {"Utilities"}
        else:
            primary_categories = {"Travel", "Foreign Spend"}
            fallback_categories = set()
        relevant = co[
            co["merchant_a_category"].isin(primary_categories)
            | co["merchant_b_category"].isin(primary_categories)
        ]
        if relevant.empty and fallback_categories:
            relevant = co[
                co["merchant_a_category"].isin(fallback_categories)
                | co["merchant_b_category"].isin(fallback_categories)
            ]
        if len(relevant):
            co = relevant
        pair = co.iloc[0]
        lines.append(
            f"- Top merchant co-occurrence: {pair['merchant_a']} + {pair['merchant_b']} ({int(pair['cooccurrence_count'])} windows)."
        )
    lines.append("")
    return lines


def write_report(
    df: pd.DataFrame,
    category: pd.DataFrame,
    features: pd.DataFrame,
    scores: pd.DataFrame,
    forecasts: pd.DataFrame,
    recurring: pd.DataFrame,
    city_drift: pd.DataFrame,
    cooccurrence: pd.DataFrame,
    velocity_tables: dict[str, pd.DataFrame],
    model_results: dict[str, Any],
) -> None:
    lines: list[str] = [
        "# LifeLine ML Study",
        "",
        "This study translates the hackathon idea into measurable machine-learning style signals from the two mock bank statements.",
        "",
        "## ML Concepts Used",
        "",
        "- **Feature engineering:** raw transactions become spend, income, month, category totals, merchant counts, city drift, FX counts, and recurrence features.",
        "- **Exploratory data analysis:** category totals, monthly spend, city mix, and merchant co-occurrence explain the data before modeling.",
        "- **Unsupervised learning:** monthly behavior vectors are clustered into normal months vs event-heavy months.",
        "- **Supervised classification:** a `RandomForestClassifier` is trained on labelled rolling transaction windows to classify `normal`, `moving_renovation`, and `travel_prep` behavior.",
        "- **Regression/forecasting:** monthly spend is forecast with linear regression when sklearn is available, otherwise a moving average fallback.",
        "- **Model validation thinking:** a real model would need many labelled customers and train/test validation. This PoC focuses on explainability and correct signal design.",
        "",
    ]

    lines.extend(answer_business_questions(scores, features, model_results))

    lines.extend(
        [
            "## Trained ML Classifier",
            "",
            f"Status: {model_results['status']}",
            "",
        ]
    )

    if model_results.get("accuracy") is not None:
        lines.extend(
            [
                f"Hold-out accuracy: **{model_results['accuracy']:.3f}**",
                "",
                "The model is a `RandomForestClassifier` trained on 45-day rolling transaction windows. This creates enough demo samples to show the full scikit-learn workflow, but the labels are synthetic labels derived from the mock scenario.",
                "",
                "Important caveat: the high accuracy is expected because this is a tiny synthetic dataset with overlapping windows. It proves the implementation flow, not production-level performance.",
                "",
                "### Classification Report",
                "",
                markdown_table(model_results["report"]),
                "",
                "### Confusion Matrix",
                "",
                markdown_table(model_results["confusion"]),
                "",
                "### Top Model Features",
                "",
                markdown_table(model_results["feature_importance"]),
                "",
                "### Latest Window Predictions",
                "",
                markdown_table(model_results["latest_predictions"]),
                "",
            ]
        )

    lines.extend(
        [
        "## Dataset Overview",
        "",
        ]
    )

    overview = (
        df.groupby("customer_id")
        .agg(
            transactions=("transaction_id", "count"),
            start=("date", "min"),
            end=("date", "max"),
            income=("income", "sum"),
            spend=("spend", "sum"),
        )
    )
    overview[["income", "spend"]] = overview[["income", "spend"]].round(2)
    lines.append(markdown_table(overview))
    lines.extend(["", "## Spend By Category", "", markdown_table(category), ""])

    for _, score_row in scores.iterrows():
        customer = score_row["customer_id"]
        feature_row = features[features["customer_id"] == customer].iloc[0]
        forecast_row = forecasts[forecasts["customer_id"] == customer].iloc[0]
        lines.extend(
            explain_customer(
                customer=customer,
                features=feature_row,
                scores=score_row,
                forecast=forecast_row,
                velocity=velocity_tables[customer],
                recurring=recurring,
                city_drift=city_drift,
                cooccurrence=cooccurrence,
            )
        )

    lines.extend(
        [
            "## Output Files",
            "",
            "- `category_spend.png`: category comparison.",
            "- `monthly_spend.png`: monthly outflow timeline.",
            "- `maria_city_mix.png` and `tom_city_mix.png`: geographic drift evidence.",
            "- `monthly_clusters.png`: KMeans/PCA monthly behavior clusters when sklearn is available.",
            "- `features.csv`: engineered customer-level signals.",
            "- `classification_scores.csv`: life-event classifier scores.",
            "- `recurring_transactions.csv`: recurring charges.",
            "- `merchant_cooccurrence.csv`: merchant graph evidence.",
            "- `spend_forecast.csv`: spend forecast.",
            "- `model_training_samples.csv`: rolling-window supervised learning samples.",
            "- `model_classification_report.csv`: classifier validation metrics.",
            "- `model_confusion_matrix.csv`: validation confusion matrix.",
            "- `model_feature_importance.csv`: strongest learned predictors.",
            "- `model_latest_predictions.csv`: model prediction for each customer's latest window.",
            "- `profile_suggestions.json`: frontend-ready LifeLine profile cards.",
            "",
            "## Recommendation",
            "",
            "Use this PoC as the signal engine behind the demo UI. For a real KBC deployment, replace the hand-weighted classifier with a validated model trained on many consented, labelled customer histories, and keep these features as the explainability layer shown to the user.",
            "",
        ]
    )
    (OUTPUT_DIR / "ml_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    df = load_transactions()
    category = spend_by_category(df)
    monthly = monthly_model_table(df)
    recurring = recurring_transactions(df)
    city_drift = city_drift_table(df)
    cooccurrence = cooccurrence_table(df)
    features, velocity_tables = engineer_customer_features(df, recurring)
    scores = classify_life_events(features)
    clustered = cluster_months(monthly)
    forecasts = forecast_spend(monthly)
    training_samples, model_feature_columns = build_window_training_set(df)
    model_results = train_life_event_model(training_samples, model_feature_columns)
    profile_suggestions = generate_profile_suggestions(
        features=features,
        scores=scores,
        forecasts=forecasts,
        recurring=recurring,
        city_drift=city_drift,
        cooccurrence=cooccurrence,
    )

    category.to_csv(OUTPUT_DIR / "category_spend.csv")
    monthly.to_csv(OUTPUT_DIR / "monthly_features.csv", index=False)
    recurring.to_csv(OUTPUT_DIR / "recurring_transactions.csv", index=False)
    city_drift.to_csv(OUTPUT_DIR / "city_drift.csv", index=False)
    cooccurrence.to_csv(OUTPUT_DIR / "merchant_cooccurrence.csv", index=False)
    features.to_csv(OUTPUT_DIR / "features.csv", index=False)
    scores.to_csv(OUTPUT_DIR / "classification_scores.csv", index=False)
    clustered.to_csv(OUTPUT_DIR / "monthly_clusters.csv", index=False)
    forecasts.to_csv(OUTPUT_DIR / "spend_forecast.csv", index=False)
    training_samples.to_csv(OUTPUT_DIR / "model_training_samples.csv", index=False)
    model_results["report"].to_csv(
        OUTPUT_DIR / "model_classification_report.csv", index=False
    )
    model_results["confusion"].to_csv(OUTPUT_DIR / "model_confusion_matrix.csv")
    model_results["feature_importance"].to_csv(
        OUTPUT_DIR / "model_feature_importance.csv", index=False
    )
    model_results["latest_predictions"].to_csv(
        OUTPUT_DIR / "model_latest_predictions.csv", index=False
    )
    write_profile_artifact(profile_suggestions)
    for customer, table in velocity_tables.items():
        table.to_csv(OUTPUT_DIR / f"{customer.lower()}_velocity.csv", index=False)

    write_plots(df, category, monthly, clustered)
    write_report(
        df=df,
        category=category,
        features=features,
        scores=scores,
        forecasts=forecasts,
        recurring=recurring,
        city_drift=city_drift,
        cooccurrence=cooccurrence,
        velocity_tables=velocity_tables,
        model_results=model_results,
    )

    print(f"LifeLine ML study complete. Outputs written to: {OUTPUT_DIR}")
    print(scores.to_string(index=False))
    if model_results.get("accuracy") is not None:
        print()
        print(
            f"Trained classifier hold-out accuracy: {model_results['accuracy']:.3f}"
        )
        print(model_results["latest_predictions"].to_string(index=False))


if __name__ == "__main__":
    main()
