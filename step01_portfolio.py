from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR / "portfolio_config.csv"
PORTFOLIO_FILE = BASE_DIR / "portfolio.csv"
OUTPUT_FILE = BASE_DIR / "portfolio_summary.csv"


def load_inputs():
    config = pd.read_csv(CONFIG_FILE)
    portfolio = pd.read_csv(PORTFOLIO_FILE)
    return config, portfolio


def validate_inputs(config, portfolio):
    required_config = {"Account", "Invested_Amount", "Current_Value"}
    required_portfolio = {
        "Asset", "Asset_KR", "Account",
        "Weight_In_Account", "Target_Weight"
    }

    missing_config = required_config - set(config.columns)
    missing_portfolio = required_portfolio - set(portfolio.columns)

    if missing_config:
        raise ValueError(
            f"portfolio_config.csv 누락 컬럼: {sorted(missing_config)}"
        )

    if missing_portfolio:
        raise ValueError(
            f"portfolio.csv 누락 컬럼: {sorted(missing_portfolio)}"
        )

    if (config["Invested_Amount"] < 0).any():
        raise ValueError("Invested_Amount에는 음수를 입력할 수 없습니다.")

    if (config["Current_Value"] < 0).any():
        raise ValueError("Current_Value에는 음수를 입력할 수 없습니다.")

    if config["Account"].duplicated().any():
        raise ValueError("portfolio_config.csv에 중복 Account가 있습니다.")

    unknown_accounts = set(portfolio["Account"]) - set(config["Account"])
    if unknown_accounts:
        raise ValueError(
            f"portfolio.csv의 Account가 config에 없습니다: {sorted(unknown_accounts)}"
        )

    for account in portfolio["Account"].dropna().unique():
        weight_sum = portfolio.loc[
            portfolio["Account"] == account, "Weight_In_Account"
        ].sum()

        if abs(weight_sum - 100.0) > 0.01:
            raise ValueError(
                f"{account} 계좌의 Weight_In_Account 합계가 "
                f"{weight_sum:.2f}%입니다. 100%가 되어야 합니다."
            )


def calculate_portfolio(config, portfolio):
    result = portfolio.copy()

    account_values = (
        config.set_index("Account")["Current_Value"].to_dict()
    )

    result["Asset_Current_Value"] = result.apply(
        lambda row: account_values[row["Account"]]
        * row["Weight_In_Account"] / 100.0,
        axis=1,
    )

    total_invested = config["Invested_Amount"].sum()
    total_current = config["Current_Value"].sum()
    total_profit = total_current - total_invested
    total_return_pct = (
        total_profit / total_invested * 100
        if total_invested > 0 else float("nan")
    )

    result["Portfolio_Weight"] = (
        result["Asset_Current_Value"] / total_current * 100
    )

    result["Target_Gap_pp"] = (
        result["Portfolio_Weight"] - result["Target_Weight"]
    )

    def target_status(row):
        if pd.isna(row["Target_Weight"]):
            return "TARGET_NOT_SET"

        gap = row["Target_Gap_pp"]

        if abs(gap) <= 0.10:
            return "ON_TARGET"
        if gap < 0:
            return "UNDERWEIGHT"
        return "OVERWEIGHT"

    result["Target_Status"] = result.apply(target_status, axis=1)

    return result, total_invested, total_current, total_profit, total_return_pct


def print_summary(
    result,
    total_invested,
    total_current,
    total_profit,
    total_return_pct,
):
    print()
    print("=" * 78)
    print("PORTFOLIO INTELLIGENCE SYSTEM - STEP 01")
    print("=" * 78)
    print(f"총 투자원금 : {total_invested:,.0f}원")
    print(f"총 평가금액 : {total_current:,.0f}원")
    print(f"총 평가손익 : {total_profit:+,.0f}원")
    print(f"총 수익률   : {total_return_pct:+.2f}%")
    print("-" * 78)

    for _, row in result.iterrows():
        target = (
            "-"
            if pd.isna(row["Target_Weight"])
            else f"{row['Target_Weight']:.2f}%"
        )

        gap = (
            "-"
            if pd.isna(row["Target_Gap_pp"])
            else f"{row['Target_Gap_pp']:+.2f}%p"
        )

        print(
            f"{row['Asset_KR']:<8} | "
            f"{row['Asset_Current_Value']:>12,.0f}원 | "
            f"현재 {row['Portfolio_Weight']:>6.2f}% | "
            f"목표 {target:>7} | "
            f"차이 {gap:>8} | "
            f"{row['Target_Status']}"
        )

    print("-" * 78)

    gold = result[result["Asset"] == "Gold"]
    if not gold.empty and not pd.isna(gold.iloc[0]["Target_Weight"]):
        g = gold.iloc[0]
        print(
            f"금 비중: 현재 {g['Portfolio_Weight']:.2f}% / "
            f"목표 {g['Target_Weight']:.2f}% / "
            f"차이 {g['Target_Gap_pp']:+.2f}%p / "
            f"{g['Target_Status']}"
        )

    print("=" * 78)
    print(f"상세 결과 저장: {OUTPUT_FILE.name}")


def main():
    config, portfolio = load_inputs()
    validate_inputs(config, portfolio)

    (
        result,
        total_invested,
        total_current,
        total_profit,
        total_return_pct,
    ) = calculate_portfolio(config, portfolio)

    result.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print_summary(
        result,
        total_invested,
        total_current,
        total_profit,
        total_return_pct,
    )


if __name__ == "__main__":
    main()
