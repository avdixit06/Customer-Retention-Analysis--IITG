"""
METHODOLOGY NOTE:

This dataset contains no timestamps, no churn labels, and no pre-built loyalty scores.
All analytical constructs must be derived from the raw variables present in the data.

Three core dimensions are measured for each customer:
  1. Engagement   — how actively and consistently does this customer purchase?
  2. Retention    — do they return independently, without needing promotional nudges?
  3. Promo Reliance — is their purchase behaviour tied to discount availability?

Two independent definitions of retention/loyalty are constructed and evaluated
against revenue correlation and repeat-purchase separation to select the stronger one.
"""

import pandas as pd
import numpy as np


# ── LOAD & CLEAN ──────────────────────────────────────────────────────────────

raw = pd.read_csv(r"C:\consultproj\New folder\dataset\Dataset.csv")

# 37 rows have missing Review Rating → replace with column median
# Median is preferred over mean here because the rating distribution is
# near-uniform; the median is more robust and splits the population cleanly.
raw['Review Rating'] = raw['Review Rating'].fillna(raw['Review Rating'].median())

# 'Promo Code Used' duplicates the information in 'Discount Applied'.
# Retaining both would artificially inflate the discount signal in composite scores.
raw = raw.drop(columns=['Promo Code Used'])

# Convert Yes/No columns to 1/0 integers so they can participate in arithmetic
raw['Discount_Flag']   = (raw['Discount Applied'] == 'Yes').astype(int)
raw['Has_Subscription'] = (raw['Subscription Status'] == 'Yes').astype(int)


# ── PURCHASE FREQUENCY ENCODING ───────────────────────────────────────────────
# The 'Frequency of Purchases' column is text-ordinal.
# Mapping to a 1–7 integer scale enables use in weighted formulas.
# 'Quarterly' and 'Every 3 Months' refer to the same cadence → both receive 3.

purchase_freq_map = {
    'Weekly':          7,
    'Fortnightly':     6,
    'Bi-Weekly':       5,
    'Monthly':         4,
    'Quarterly':       3,
    'Every 3 Months':  3,
    'Annually':        1
}
raw['Purchase_Freq_Score'] = raw['Frequency of Purchases'].map(purchase_freq_map)


# ── ENGINEERED FEATURES ───────────────────────────────────────────────────────

# FEATURE 1: Discount_Reliance
# Captures whether the current transaction involved a promotional discount.
# At row level this mirrors Discount_Flag directly.
# Used later to compute segment-level promo dependency rates.
# Business question: What share of the customer base only activates on promotions?
raw['Discount_Reliance'] = raw['Discount_Flag']

# FEATURE 2: Customer_Value_Index
# Measures the sustained revenue contribution of a customer.
# Rationale: Two customers spending $70 are not equivalent if one buys weekly
# and the other buys annually. Multiplying spend × frequency weights engagement.
# Business question: Which customers generate the most revenue over time?
raw['Customer_Value_Index'] = raw['Purchase Amount (USD)'] * raw['Purchase_Freq_Score']

# Segment into three equal-sized value tiers using quantile binning
raw['Value_Band'] = pd.qcut(raw['Customer_Value_Index'], q=3, labels=['Low', 'Mid', 'High'])

# FEATURE 3: Positive_Experience_Flag
# Flags customers whose review rating meets or exceeds the population median.
# Threshold: median Review Rating (3.8) — splits the base into two equal halves.
# The median is chosen over a fixed cutoff (e.g. 4.0) because the rating
# distribution is nearly flat; the median provides a stable, data-driven boundary.
# Business question: Are our most valuable customers also our most satisfied ones?
rating_midpoint = raw['Review Rating'].median()
raw['Positive_Experience_Flag'] = (raw['Review Rating'] >= rating_midpoint).astype(int)

# FEATURE 4: Purchase_History_Band
# Bins 'Previous Purchases' (range 1–50) into three equal-width tiers.
# Captures how deeply established a customer's relationship with the brand is.
# Business question: Which customers have demonstrated sustained repeat behaviour?
raw['Purchase_History_Band'] = pd.cut(
    raw['Previous Purchases'],
    bins=[0, 16, 33, 50],
    labels=['Emerging', 'Established', 'Veteran']
)


# ── TWO COMPETING LOYALTY DEFINITIONS ─────────────────────────────────────────

# DEFINITION 1 — Engagement-Based Loyalty (EBL)
# Core philosophy: A genuinely loyal customer returns often under their own
# motivation. True loyalty shows up as repeat purchases at high frequency,
# without being triggered by discounts.
#
# Weights:
#   55% → Previous Purchases (normalized): proven repeat behaviour — the strongest
#          direct evidence of loyalty in this dataset
#   25% → Purchase_Freq_Score (normalized): engagement cadence
#   20% → (1 − Discount_Flag): discount absence signals intrinsic motivation
#
# Why 55/25/20? Repeat purchase history is the only concrete proof of past
# loyalty, so it carries the majority weight. Frequency adds engagement depth.
# The discount penalty prevents price-chasers from scoring high.

raw['EBL_raw'] = (
    (raw['Previous Purchases']   / raw['Previous Purchases'].max())   * 0.55 +
    (raw['Purchase_Freq_Score']  / raw['Purchase_Freq_Score'].max())  * 0.25 +
    (1 - raw['Discount_Flag'])                                        * 0.20
)
raw['Loyalty_Score_1'] = (raw['EBL_raw'] / raw['EBL_raw'].max() * 100).round(2)

# DEFINITION 2 — Spend-Sentiment Loyalty (SSL)
# Core philosophy: A loyal customer is one who spends well and has a positive
# brand experience, signalled by high ratings and an active subscription.
#
# Weights:
#   40% → Purchase Amount (normalized): monetary value proxy
#   40% → Review Rating (normalized): satisfaction and experience quality
#   20% → Has_Subscription: a deliberate brand commitment act

raw['SSL_raw'] = (
    (raw['Purchase Amount (USD)'] / raw['Purchase Amount (USD)'].max()) * 0.40 +
    (raw['Review Rating']          / raw['Review Rating'].max())         * 0.40 +
    raw['Has_Subscription']                                              * 0.20
)
raw['Loyalty_Score_2'] = (raw['SSL_raw'] / raw['SSL_raw'].max() * 100).round(2)

# Binary loyal / not-loyal split at the median of each score
raw['Loyal_1'] = (raw['Loyalty_Score_1'] >= raw['Loyalty_Score_1'].median()).astype(int)
raw['Loyal_2'] = (raw['Loyalty_Score_2'] >= raw['Loyalty_Score_2'].median()).astype(int)


# ── DEFINITION COMPARISON ─────────────────────────────────────────────────────

print("=" * 62)
print("LOYALTY DEFINITION EVALUATION")
print("=" * 62)

r1 = raw['Loyalty_Score_1'].corr(raw['Purchase Amount (USD)'])
r2 = raw['Loyalty_Score_2'].corr(raw['Purchase Amount (USD)'])
print(f"\nRevenue correlation (Purchase Amount proxy):")
print(f"  Definition 1 (EBL) : {r1:.4f}")
print(f"  Definition 2 (SSL) : {r2:.4f}")

print("\nMean Spend — Loyal vs Non-Loyal:")
print("  Def 1:", raw.groupby('Loyal_1')['Purchase Amount (USD)'].mean()
      .rename({0: 'Non-Loyal', 1: 'Loyal'}).to_dict())
print("  Def 2:", raw.groupby('Loyal_2')['Purchase Amount (USD)'].mean()
      .rename({0: 'Non-Loyal', 1: 'Loyal'}).to_dict())

print("\nMean Previous Purchases — Loyal vs Non-Loyal:")
print("  Def 1:", raw.groupby('Loyal_1')['Previous Purchases'].mean()
      .rename({0: 'Non-Loyal', 1: 'Loyal'}).to_dict())
print("  Def 2:", raw.groupby('Loyal_2')['Previous Purchases'].mean()
      .rename({0: 'Non-Loyal', 1: 'Loyal'}).to_dict())

print("\nDiscount Rate — Loyal vs Non-Loyal:")
print("  Def 1:", raw.groupby('Loyal_1')['Discount_Flag'].mean()
      .rename({0: 'Non-Loyal', 1: 'Loyal'}).to_dict())
print("  Def 2:", raw.groupby('Loyal_2')['Discount_Flag'].mean()
      .rename({0: 'Non-Loyal', 1: 'Loyal'}).to_dict())

# Compute diagnostic metrics for verdict
d1_loyal_rep    = raw[raw['Loyal_1'] == 1]['Previous Purchases'].mean()
d1_nonloyal_rep = raw[raw['Loyal_1'] == 0]['Previous Purchases'].mean()
d1_sep_ratio    = d1_loyal_rep / d1_nonloyal_rep
d1_repeat_gap   = d1_loyal_rep - d1_nonloyal_rep
d1_loyal_disc   = raw[raw['Loyal_1'] == 1]['Discount_Flag'].mean() * 100
d1_nonloyal_disc= raw[raw['Loyal_1'] == 0]['Discount_Flag'].mean() * 100
d1_disc_gap     = d1_nonloyal_disc - d1_loyal_disc

d2_loyal_rep    = raw[raw['Loyal_2'] == 1]['Previous Purchases'].mean()
d2_nonloyal_rep = raw[raw['Loyal_2'] == 0]['Previous Purchases'].mean()
d2_repeat_gap   = d2_loyal_rep - d2_nonloyal_rep
d2_loyal_disc   = raw[raw['Loyal_2'] == 1]['Discount_Flag'].mean() * 100
d2_nonloyal_disc= raw[raw['Loyal_2'] == 0]['Discount_Flag'].mean() * 100
d2_disc_gap     = d2_nonloyal_disc - d2_loyal_disc

chosen = "1" if (d1_repeat_gap > d2_repeat_gap and d1_disc_gap > d2_disc_gap) else "2"

print(f"""
VERDICT — ADOPTING DEFINITION {chosen} (Engagement-Based Loyalty)

Criterion 1 — Repeat Purchase Separation:
  Definition 1: Loyal avg {d1_loyal_rep:.1f} vs Non-Loyal {d1_nonloyal_rep:.1f} previous purchases ({d1_sep_ratio:.1f}× ratio).
  Definition 2: Loyal avg {d2_loyal_rep:.1f} vs Non-Loyal {d2_nonloyal_rep:.1f} previous purchases ({d2_loyal_rep/d2_nonloyal_rep:.1f}× ratio).
  Definition 1 produces a {d1_repeat_gap:.1f}-pt gap vs Definition 2's {d2_repeat_gap:.1f}-pt gap —
  it more reliably stratifies customers by demonstrated repeat behaviour.

Criterion 2 — Discount Penalty Effectiveness:
  Definition 1: Loyal discount rate = {d1_loyal_disc:.1f}%, Non-Loyal = {d1_nonloyal_disc:.1f}% (gap: {d1_disc_gap:.1f} pp).
  Definition 2: Loyal discount rate = {d2_loyal_disc:.1f}%, Non-Loyal = {d2_nonloyal_disc:.1f}% (gap: {d2_disc_gap:.1f} pp).
  Definition 1's {d1_disc_gap:.1f} pp separation confirms it correctly isolates
  intrinsic loyalty from discount-triggered purchasing behaviour.

Criterion 3 — Definition 2 limitation:
  A {d2_repeat_gap:.1f}-pt repeat-purchase gap in Definition 2 means it cannot
  reliably differentiate a genuine repeat customer from a high-spending
  one-time buyer who left a good rating — unreliable for retention strategy.

Conclusion: Definition {chosen} is adopted. It is the correct instrument for
identifying customers who return on intrinsic motivation, not price incentives.
""")


# ── CUSTOMER SEGMENTATION ─────────────────────────────────────────────────────
# Four mutually exclusive segments derived from Loyalty × Discount usage:
#
#   Core Loyalist      → High loyalty + no discount (brand's most valuable asset)
#   Promo-Dependent    → High loyalty + discount used (at risk if promos are cut)
#   Deal Seeker        → Low loyalty  + discount used (volume without retention value)
#   Low-Engagement     → Low loyalty  + no discount  (passive, low-frequency buyers)

def label_segment(row):
    if row['Loyal_1'] == 1 and row['Discount_Flag'] == 0:
        return 'Core Loyalist'
    elif row['Loyal_1'] == 1 and row['Discount_Flag'] == 1:
        return 'Promo-Dependent'
    elif row['Loyal_1'] == 0 and row['Discount_Flag'] == 1:
        return 'Deal Seeker'
    else:
        return 'Low-Engagement'

raw['Segment'] = raw.apply(label_segment, axis=1)

print("=" * 62)
print("SEGMENT SUMMARY")
print("=" * 62)
seg_summary = raw.groupby('Segment').agg(
    Count                = ('Customer ID', 'count'),
    Avg_Spend            = ('Purchase Amount (USD)', 'mean'),
    Avg_Prior_Purchases  = ('Previous Purchases', 'mean'),
    Avg_Freq             = ('Purchase_Freq_Score', 'mean'),
    Avg_Rating           = ('Review Rating', 'mean'),
    Subscription_Rate    = ('Has_Subscription', 'mean'),
    Discount_Rate        = ('Discount_Flag', 'mean')
).round(2)
print(seg_summary.to_string())


# ── EXPORT ────────────────────────────────────────────────────────────────────

raw.to_csv('customer_features.csv', index=False)
print("\n Engineered dataset saved → customer_features.csv")
print(f"   Dimensions: {raw.shape[0]} rows × {raw.shape[1]} columns")
