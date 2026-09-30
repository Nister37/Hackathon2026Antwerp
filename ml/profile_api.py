"""Generate the small, explainable profile artifact consumed by Spring Boot.

Run from the repository root with ``python -m ml.profile_api``. This is a
one-shot batch job, not a second public API. Spring owns all HTTP endpoints.
"""

from __future__ import annotations

import os
from pathlib import Path

from .ml_study import (
    BASE_DIR,
    classify_life_events,
    city_drift_table,
    cooccurrence_table,
    engineer_customer_features,
    forecast_spend,
    generate_profile_suggestions,
    load_transactions,
    monthly_model_table,
    recurring_transactions,
    write_profile_artifact,
)


def main() -> None:
    transactions = load_transactions()
    recurring = recurring_transactions(transactions)
    features, _ = engineer_customer_features(transactions, recurring)
    suggestions = generate_profile_suggestions(
        features=features,
        scores=classify_life_events(features),
        forecasts=forecast_spend(monthly_model_table(transactions)),
        recurring=recurring,
        city_drift=city_drift_table(transactions),
        cooccurrence=cooccurrence_table(transactions),
    )
    output_dir = Path(os.environ.get("ML_PROFILE_DIR", BASE_DIR))
    print(f"Generated {len(suggestions)} demo profiles: {write_profile_artifact(suggestions, output_dir)}")


if __name__ == "__main__":
    main()
