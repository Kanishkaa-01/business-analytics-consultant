import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

def generate_samples():
    sample_dir = Path(__file__).parent
    sample_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)

    # -----------------------------------------------------------------
    # Dataset 1: Omnichannel Retail E-commerce (1,200 records)
    # -----------------------------------------------------------------
    n1 = 1200
    start_date = datetime(2025, 1, 1)
    dates = [start_date + timedelta(days=int(i * 0.3)) for i in range(n1)]
    
    categories = ["Electronics", "Apparel", "Home & Kitchen", "Health & Beauty", "Footwear"]
    regions = ["North America", "Europe", "Asia Pacific", "Latin America"]
    channels = ["Direct Online", "Marketplace", "Wholesale B2B"]
    customer_tiers = ["Enterprise", "Mid-Market", "Consumer Basic", "VIP Retail"]

    records_1 = []
    for i in range(n1):
        cat = np.random.choice(categories, p=[0.25, 0.30, 0.20, 0.15, 0.10])
        reg = np.random.choice(regions, p=[0.40, 0.30, 0.20, 0.10])
        chan = np.random.choice(channels, p=[0.45, 0.35, 0.20])
        tier = np.random.choice(customer_tiers, p=[0.15, 0.25, 0.45, 0.15])
        
        # Base pricing
        if cat == "Electronics":
            unit_price = np.random.uniform(180, 850)
            # Commercial drag: Marketplace electronics experienced aggressive discounting in second half
            is_second_half = i > (n1 * 0.5)
            discount = np.random.uniform(0.18, 0.38) if (is_second_half and chan == "Marketplace") else np.random.uniform(0.02, 0.12)
            lead_time_days = np.random.exponential(4) + (5 if reg == "Europe" else 2)
        elif cat == "Apparel":
            unit_price = np.random.uniform(35, 160)
            discount = np.random.uniform(0.05, 0.20)
            lead_time_days = np.random.exponential(3) + 2
        else:
            unit_price = np.random.uniform(25, 220)
            discount = np.random.uniform(0.0, 0.15)
            lead_time_days = np.random.exponential(3) + 2

        qty = np.random.randint(1, 12) if tier in ["Consumer Basic", "VIP Retail"] else np.random.randint(15, 60)
        gross_sales = round(unit_price * qty, 2)
        discount_amount = round(gross_sales * discount, 2)
        net_revenue = round(gross_sales - discount_amount, 2)
        cost_of_goods = round(gross_sales * np.random.uniform(0.48, 0.65), 2)
        shipping_cost = round(qty * np.random.uniform(3.5, 8.0) + (lead_time_days * 1.5), 2)
        profit = round(net_revenue - cost_of_goods - shipping_cost, 2)
        return_flag = 1 if np.random.rand() < (0.14 if cat == "Apparel" else 0.04) else 0

        records_1.append({
            "order_id": f"ORD-2025-{10000 + i}",
            "transaction_date": dates[i].strftime("%Y-%m-%d"),
            "region": reg,
            "category": cat,
            "sales_channel": chan,
            "customer_tier": tier,
            "quantity": qty,
            "unit_price": round(unit_price, 2),
            "discount_rate": round(discount, 3),
            "gross_sales": gross_sales,
            "net_revenue": net_revenue,
            "cost_of_goods": cost_of_goods,
            "shipping_cost": shipping_cost,
            "net_profit": profit,
            "lead_time_days": round(lead_time_days, 1),
            "returned": return_flag
        })

    df1 = pd.DataFrame(records_1)
    df1.to_csv(sample_dir / "retail_ecommerce_q3.csv", index=False)
    print(f"Generated retail_ecommerce_q3.csv ({len(df1)} rows)")

    # -----------------------------------------------------------------
    # Dataset 2: B2B SaaS ARR and Churn Analysis (800 accounts)
    # -----------------------------------------------------------------
    n2 = 800
    industries = ["FinTech", "Healthcare IT", "E-Commerce Tech", "Logistics", "EdTech"]
    plans = ["Starter", "Professional", "Enterprise", "Global Scale"]
    
    records_2 = []
    for i in range(n2):
        ind = np.random.choice(industries)
        plan = np.random.choice(plans, p=[0.20, 0.40, 0.30, 0.10])
        arr = np.random.uniform(6000, 24000) if plan == "Starter" else (
            np.random.uniform(25000, 75000) if plan == "Professional" else np.random.uniform(80000, 250000)
        )
        tenure_months = np.random.randint(3, 48)
        daily_active_users = np.random.randint(5, 45) if plan == "Starter" else np.random.randint(40, 350)
        support_tickets = np.random.poisson(3) + (4 if tenure_months < 6 else 0)
        nps_score = np.random.randint(1, 10)
        feature_adoption_pct = np.random.uniform(25, 95)
        
        # Churn driver: high tickets + low adoption = high churn
        churn_prob = 0.08
        if support_tickets > 6 and feature_adoption_pct < 50:
            churn_prob = 0.55
        elif nps_score <= 4:
            churn_prob = 0.40
        elif plan == "Starter":
            churn_prob = 0.22

        churned = 1 if np.random.rand() < churn_prob else 0
        expansion_arr = round(arr * np.random.uniform(0.1, 0.3), 2) if (churned == 0 and feature_adoption_pct > 75) else 0.0

        records_2.append({
            "account_id": f"ACC-{20000 + i}",
            "industry": ind,
            "subscription_plan": plan,
            "arr_dollars": round(arr, 2),
            "tenure_months": tenure_months,
            "daily_active_users": daily_active_users,
            "support_tickets_raised": support_tickets,
            "nps_satisfaction": nps_score,
            "feature_adoption_pct": round(feature_adoption_pct, 1),
            "expansion_arr": expansion_arr,
            "churn_flag": churned
        })

    df2 = pd.DataFrame(records_2)
    df2.to_csv(sample_dir / "b2b_saas_churn.csv", index=False)
    print(f"Generated b2b_saas_churn.csv ({len(df2)} rows)")

    # -----------------------------------------------------------------
    # Dataset 3: Manufacturing Operations & Supply Chain (950 batches)
    # -----------------------------------------------------------------
    n3 = 950
    facilities = ["Plant Detroit", "Plant Stuttgart", "Plant Shanghai", "Plant Monterrey"]
    suppliers = ["Apex Materials", "Titan Alloy Co", "Global Poly", "Nexus Chemical"]
    materials = ["High-Tensile Steel", "Carbon Composite", "Polymer Resin", "Aluminum Alloy"]

    records_3 = []
    for i in range(n3):
        fac = np.random.choice(facilities)
        sup = np.random.choice(suppliers)
        mat = np.random.choice(materials)
        batch_size_units = np.random.randint(500, 5000)
        cycle_time_hours = np.random.normal(14.5, 2.5) + (3.5 if fac == "Plant Shanghai" else 0)
        downtime_minutes = np.random.exponential(45)
        
        # Supplier defect correlation
        defect_rate = np.random.uniform(0.008, 0.025)
        if sup == "Nexus Chemical":
            defect_rate += np.random.uniform(0.02, 0.05)  # Quality flaw

        defective_units = int(batch_size_units * defect_rate)
        scrap_cost = round(defective_units * np.random.uniform(45, 110), 2)
        total_production_cost = round(batch_size_units * np.random.uniform(32, 68) + scrap_cost, 2)
        on_time_delivery = 0 if cycle_time_hours > 17.5 else 1

        records_3.append({
            "batch_id": f"BAT-{30000 + i}",
            "facility": fac,
            "supplier": sup,
            "raw_material": mat,
            "batch_size_units": batch_size_units,
            "cycle_time_hours": round(cycle_time_hours, 2),
            "downtime_minutes": round(downtime_minutes, 1),
            "defect_rate_pct": round(defect_rate * 100, 2),
            "defective_units": defective_units,
            "scrap_cost_dollars": scrap_cost,
            "total_production_cost": total_production_cost,
            "on_time_delivery_flag": on_time_delivery
        })

    df3 = pd.DataFrame(records_3)
    df3.to_csv(sample_dir / "manufacturing_supply.csv", index=False)
    print(f"Generated manufacturing_supply.csv ({len(df3)} rows)")

if __name__ == "__main__":
    generate_samples()
