"""
Preprocessing utilities for the AI Loan Decision Platform ML pipeline.

Handles feature engineering from the Give Me Some Credit dataset and
input transformation for inference (converting LoanApplicationInput
to model-ready numpy arrays).

Feature mapping (10 application features):
1. age - direct from dataset
2. monthly_income - from MonthlyIncome
3. employment_status - derived/encoded (categorical)
4. employment_length - derived from age
5. credit_score - synthesized/scaled from credit lines and delinquency
6. existing_loans - from NumberOfOpenCreditLinesAndLoans
7. monthly_emi - derived from DebtRatio * MonthlyIncome
8. dti_ratio - from DebtRatio (scaled to 0-100)
9. credit_utilization - from RevolvingUtilizationOfUnsecuredLines (scaled to 0-100, capped)
10. loan_amount_requested - derived
"""

import numpy as np
import pandas as pd

# Ordered feature names used by the trained models
FEATURE_NAMES = [
    "age",
    "monthly_income",
    "employment_status_encoded",
    "employment_length",
    "credit_score",
    "existing_loans",
    "monthly_emi",
    "dti_ratio",
    "credit_utilization",
    "loan_amount_requested",
]

# Employment status encoding map
EMPLOYMENT_STATUS_MAP = {
    "Employed": 3,
    "Self-Employed": 2,
    "Retired": 1,
    "Unemployed": 0,
}


def preprocess_kaggle_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Preprocess the Give Me Some Credit dataset into our 10-feature format.

    Steps:
    1. Handle missing values (median imputation)
    2. Cap outliers
    3. Engineer/derive the 10 application features

    Args:
        df: Raw dataframe from the Give Me Some Credit dataset.

    Returns:
        Tuple of (features DataFrame with 10 columns, target Series).
    """
    # Drop the unnamed index column if present
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # Extract target
    target = df["SeriousDlqin2yrs"].copy()

    # --- Handle missing values ---
    df["MonthlyIncome"] = df["MonthlyIncome"].fillna(df["MonthlyIncome"].median())
    df["NumberOfDependents"] = df["NumberOfDependents"].fillna(
        df["NumberOfDependents"].median()
    )

    # --- Cap outliers ---
    # Cap RevolvingUtilizationOfUnsecuredLines at 1.5 (150%)
    df["RevolvingUtilizationOfUnsecuredLines"] = df[
        "RevolvingUtilizationOfUnsecuredLines"
    ].clip(upper=1.5)

    # Cap DebtRatio at 1.0 (100%)
    df["DebtRatio"] = df["DebtRatio"].clip(upper=1.0)

    # Cap MonthlyIncome at 50000
    df["MonthlyIncome"] = df["MonthlyIncome"].clip(upper=50000)

    # Cap age between 18 and 100
    df["age"] = df["age"].clip(lower=18, upper=100)

    # Cap delinquency counts at 20
    for col in [
        "NumberOfTime30-59DaysPastDueNotWorse",
        "NumberOfTimes90DaysLate",
        "NumberOfTime60-89DaysPastDueNotWorse",
    ]:
        df[col] = df[col].clip(upper=20)

    # --- Feature Engineering: Map to 10 application features ---

    features = pd.DataFrame()

    # 1. age - direct
    features["age"] = df["age"]

    # 2. monthly_income - direct from MonthlyIncome
    features["monthly_income"] = df["MonthlyIncome"]

    # 3. employment_status_encoded - derive from age and income
    # Heuristic: Retired if age >= 65, Unemployed if income < 500,
    # Self-Employed if income > 15000, else Employed
    conditions = [
        df["age"] >= 65,
        df["MonthlyIncome"] < 500,
        df["MonthlyIncome"] > 15000,
    ]
    choices = [
        EMPLOYMENT_STATUS_MAP["Retired"],
        EMPLOYMENT_STATUS_MAP["Unemployed"],
        EMPLOYMENT_STATUS_MAP["Self-Employed"],
    ]
    features["employment_status_encoded"] = np.select(
        conditions, choices, default=EMPLOYMENT_STATUS_MAP["Employed"]
    )

    # 4. employment_length - derive from age (assume started working at ~20)
    features["employment_length"] = (df["age"] - 20).clip(lower=0, upper=50)

    # 5. credit_score - synthesize from delinquency history and credit lines
    # Base score 650, penalize for delinquencies, reward for credit lines
    delinquency_total = (
        df["NumberOfTime30-59DaysPastDueNotWorse"]
        + df["NumberOfTimes90DaysLate"] * 2
        + df["NumberOfTime60-89DaysPastDueNotWorse"] * 1.5
    )
    credit_lines_bonus = df["NumberOfOpenCreditLinesAndLoans"].clip(upper=20) * 3
    raw_score = 650 - (delinquency_total * 15) + credit_lines_bonus
    features["credit_score"] = raw_score.clip(lower=300, upper=850).astype(int)

    # 6. existing_loans - from NumberOfOpenCreditLinesAndLoans (cap at 50)
    features["existing_loans"] = df["NumberOfOpenCreditLinesAndLoans"].clip(upper=50)

    # 7. monthly_emi - derived from DebtRatio * MonthlyIncome
    features["monthly_emi"] = (df["DebtRatio"] * df["MonthlyIncome"]).clip(lower=0)

    # 8. dti_ratio - DebtRatio scaled to 0-100
    features["dti_ratio"] = (df["DebtRatio"] * 100).clip(lower=0, upper=100)

    # 9. credit_utilization - RevolvingUtilizationOfUnsecuredLines scaled to 0-100
    features["credit_utilization"] = (
        df["RevolvingUtilizationOfUnsecuredLines"] * 100
    ).clip(lower=0, upper=100)

    # 10. loan_amount_requested - derive from monthly income * factor
    # Use a reasonable proxy: 12 months of income as typical loan request
    features["loan_amount_requested"] = (df["MonthlyIncome"] * 12).clip(
        lower=1, upper=10_000_000
    )

    return features, target


def transform_application_input(application_data: dict) -> np.ndarray:
    """
    Transform a LoanApplicationInput dictionary into a model-ready numpy array.

    This function is used at inference time to convert the API input
    into the same feature format the model was trained on.

    Args:
        application_data: Dictionary with keys matching LoanApplicationInput fields.

    Returns:
        1D numpy array with 10 features in the correct order.
    """
    # Encode employment status
    employment_encoded = EMPLOYMENT_STATUS_MAP.get(
        application_data.get("employment_status", "Employed"),
        EMPLOYMENT_STATUS_MAP["Employed"],
    )

    features = np.array(
        [
            application_data["age"],
            application_data["monthly_income"],
            employment_encoded,
            application_data["employment_length"],
            application_data["credit_score"],
            application_data["existing_loans"],
            application_data["monthly_emi"],
            application_data["dti_ratio"],
            application_data["credit_utilization"],
            application_data["loan_amount_requested"],
        ],
        dtype=np.float64,
    )

    return features
