-- ============================================================
--  Source Table : customer_features  (from customer_features.csv)
--  Engine       : SQLite  (minor adjustments needed for PostgreSQL)
-- ============================================================


-- ------------------------------------------------------------
-- Q1A — Value Band Profile: What distinguishes high-value
--        customers from low-value ones?
-- LOGIC: Group by Value_Band and compare key behavioral
--        metrics across spend, engagement, satisfaction,
--        and promo reliance to identify the value drivers.
-- ------------------------------------------------------------

SELECT
    Value_Band,
    COUNT(*)                                        AS Total_Customers,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    ROUND(AVG(Purchase_Freq_Score), 2)              AS Mean_Freq_Score,
    ROUND(AVG("Review Rating"), 2)                  AS Mean_Rating,
    ROUND(AVG(Has_Subscription) * 100, 1)           AS Subscription_Pct,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct,
    ROUND(AVG(Positive_Experience_Flag) * 100, 1)   AS Satisfied_Pct
FROM customer_features
GROUP BY Value_Band
ORDER BY CASE Value_Band
    WHEN 'High' THEN 1
    WHEN 'Mid'  THEN 2
    WHEN 'Low'  THEN 3
END;


-- ------------------------------------------------------------
-- Q1B — Segment Revenue Breakdown
-- LOGIC: Segments are derived from Loyalty (Def 1) × Discount
--        usage. Revenue share reveals how dependent the brand
--        actually is on each segment for its top line.
-- ------------------------------------------------------------

SELECT
    Segment,
    COUNT(*)                                                AS Total_Customers,
    ROUND(COUNT(*) * 100.0 / 3900, 1)                      AS Share_Of_Base_Pct,
    ROUND(AVG("Purchase Amount (USD)"), 2)                  AS Mean_Spend,
    ROUND(AVG("Previous Purchases"), 2)                     AS Mean_Prior_Purchases,
    ROUND(AVG(Purchase_Freq_Score), 2)                      AS Mean_Freq_Score,
    ROUND(AVG("Review Rating"), 2)                          AS Mean_Rating,
    ROUND(AVG(Has_Subscription) * 100, 1)                   AS Subscription_Pct,
    ROUND(AVG(Discount_Flag) * 100, 1)                      AS Promo_Usage_Pct,
    ROUND(
        SUM("Purchase Amount (USD)") * 1.0 /
        (SELECT SUM("Purchase Amount (USD)") FROM customer_features) * 100
    , 1)                                                    AS Revenue_Contribution_Pct
FROM customer_features
GROUP BY Segment
ORDER BY Mean_Prior_Purchases DESC;


-- ------------------------------------------------------------
-- Q2A — Season × Purchase History Band Cross-Tab
-- LOGIC: Examines whether certain seasons attract customers
--        with lower vs higher tenure. Discount rate per cell
--        distinguishes organic seasonal demand from
--        promotion-driven volume spikes.
-- ------------------------------------------------------------

SELECT
    Season,
    Purchase_History_Band,
    COUNT(*)                                        AS Record_Count,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct
FROM customer_features
GROUP BY Season, Purchase_History_Band
ORDER BY Season,
    CASE Purchase_History_Band
        WHEN 'Veteran'     THEN 1
        WHEN 'Established' THEN 2
        WHEN 'Emerging'    THEN 3
    END;


-- ------------------------------------------------------------
-- Q2B — Category vs Customer Tenure
-- LOGIC: Categories with high average prior purchases are
--        retention anchors (customers stay for them).
--        Categories with low averages are entry points
--        (customers discover the brand through them).
-- ------------------------------------------------------------

SELECT
    Category,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    COUNT(*)                                        AS Transaction_Count,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct,
    ROUND(AVG(Purchase_Freq_Score), 2)              AS Mean_Freq_Score,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend
FROM customer_features
GROUP BY Category
ORDER BY Mean_Prior_Purchases DESC;


-- ------------------------------------------------------------
-- Q3 — Geographic Brand Pull Analysis
-- LOGIC: Brand Affinity Index (BAI) per state:
--   35% → Mean Spend (normalised against $100 ceiling)
--   45% → (1 - Promo Rate): penalises discount-heavy states
--   20% → Mean Frequency (normalised against max 7)
-- High BAI = genuine brand affinity; Low BAI = promo-reliant volume.
-- Minimum 50 customers required for statistical reliability.
-- ------------------------------------------------------------

-- Top 15 States by Brand Affinity
SELECT
    Location,
    COUNT(*)                                        AS Customer_Count,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    ROUND(AVG(Purchase_Freq_Score), 2)              AS Mean_Freq_Score,
    ROUND(AVG(Has_Subscription) * 100, 1)           AS Subscription_Pct,
    ROUND(
        (AVG("Purchase Amount (USD)") / 100.0) * 0.35 +
        (1 - AVG(Discount_Flag))               * 0.45 +
        (AVG(Purchase_Freq_Score) / 7.0)       * 0.20
    , 4)                                            AS Brand_Affinity_Index
FROM customer_features
GROUP BY Location
HAVING Customer_Count >= 50
ORDER BY Brand_Affinity_Index DESC
LIMIT 15;

-- Bottom 10 States — Highest Promo Dependency
SELECT
    Location,
    COUNT(*)                                        AS Customer_Count,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    ROUND(
        (AVG("Purchase Amount (USD)") / 100.0) * 0.35 +
        (1 - AVG(Discount_Flag))               * 0.45 +
        (AVG(Purchase_Freq_Score) / 7.0)       * 0.20
    , 4)                                            AS Brand_Affinity_Index
FROM customer_features
GROUP BY Location
HAVING Customer_Count >= 50
ORDER BY Brand_Affinity_Index ASC
LIMIT 10;


-- ------------------------------------------------------------
-- Q4 — Acquisition Predictors of Long-Term Customer Value
-- LOGIC: Profile customers by observable attributes available
--        at acquisition time (age, gender, payment method,
--        purchase frequency) against Loyalty_Score_1.
--        Goal: identify which profiles predict high loyalty
--        so acquisition targeting can be refined.
-- ------------------------------------------------------------

-- 4A: Age Cohort × Gender
SELECT
    CASE
        WHEN Age BETWEEN 18 AND 30 THEN '18–30'
        WHEN Age BETWEEN 31 AND 45 THEN '31–45'
        WHEN Age BETWEEN 46 AND 60 THEN '46–60'
        ELSE '61+'
    END                                             AS Age_Cohort,
    Gender,
    COUNT(*)                                        AS Record_Count,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    ROUND(AVG(Purchase_Freq_Score), 2)              AS Mean_Freq_Score,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct,
    ROUND(AVG(Loyalty_Score_1), 2)                  AS Mean_Loyalty_Score
FROM customer_features
GROUP BY Age_Cohort, Gender
ORDER BY Mean_Loyalty_Score DESC;

-- 4B: Payment Method
SELECT
    "Payment Method",
    COUNT(*)                                        AS Record_Count,
    ROUND(AVG(Loyalty_Score_1), 2)                  AS Mean_Loyalty_Score,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend
FROM customer_features
GROUP BY "Payment Method"
ORDER BY Mean_Loyalty_Score DESC;

-- 4C: Purchase Frequency (strongest single predictor expected)
SELECT
    "Frequency of Purchases",
    COUNT(*)                                        AS Record_Count,
    ROUND(AVG(Loyalty_Score_1), 2)                  AS Mean_Loyalty_Score,
    ROUND(AVG("Previous Purchases"), 2)             AS Mean_Prior_Purchases,
    ROUND(AVG("Purchase Amount (USD)"), 2)          AS Mean_Spend,
    ROUND(AVG(Discount_Flag) * 100, 1)              AS Promo_Usage_Pct,
    ROUND(AVG(Has_Subscription) * 100, 1)           AS Subscription_Pct
FROM customer_features
GROUP BY "Frequency of Purchases"
ORDER BY Mean_Loyalty_Score DESC;


-- ------------------------------------------------------------
-- Q5 — Ideal Customer Profile (ICP) Construction
-- LOGIC: Restricted to Core Loyalists only (Loyal_1 = 1,
--        Discount_Flag = 0 — high engagement, no promo use).
--        Profiling by demographic and behavioural attributes
--        produces a targeting-ready ICP the marketing team
--        can act on for acquisition campaigns.
-- ------------------------------------------------------------

-- 5A: Core Loyalist micro-segment breakdown
SELECT
    Gender,
    CASE
        WHEN Age BETWEEN 18 AND 30 THEN '18–30'
        WHEN Age BETWEEN 31 AND 45 THEN '31–45'
        WHEN Age BETWEEN 46 AND 60 THEN '46–60'
        ELSE '61+'
    END                                                 AS Age_Cohort,
    Category,
    "Payment Method",
    "Frequency of Purchases",
    COUNT(*)                                            AS Record_Count,
    ROUND(AVG(Loyalty_Score_1), 2)                      AS Mean_Loyalty,
    ROUND(AVG("Previous Purchases"), 2)                 AS Mean_Prior_Purchases,
    ROUND(AVG("Purchase Amount (USD)"), 2)              AS Mean_Spend,
    ROUND(AVG("Review Rating"), 2)                      AS Mean_Rating
FROM customer_features
WHERE Segment = 'Core Loyalist'
GROUP BY Gender, Age_Cohort, Category, "Payment Method", "Frequency of Purchases"
HAVING Record_Count >= 5
ORDER BY Mean_Loyalty DESC, Record_Count DESC
LIMIT 20;

-- 5B: ICP — Aggregate Portrait of a Core Loyalist
SELECT
    ROUND(AVG(Age), 1)                                  AS Avg_Age,
    ROUND(AVG("Previous Purchases"), 1)                 AS Avg_Prior_Purchases,
    ROUND(AVG(Purchase_Freq_Score), 1)                  AS Avg_Freq_Score,
    ROUND(AVG("Purchase Amount (USD)"), 1)              AS Avg_Spend,
    ROUND(AVG("Review Rating"), 1)                      AS Avg_Rating,
    ROUND(AVG(Has_Subscription) * 100, 1)               AS Subscription_Pct,
    ROUND(AVG(Discount_Flag) * 100, 1)                  AS Promo_Usage_Pct,
    COUNT(*)                                            AS Total_Core_Loyalists
FROM customer_features
WHERE Segment = 'Core Loyalist';
