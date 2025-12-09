#!/usr/bin/env python
# coding: utf-8

# In[2]:


import streamlit as st
import pandas as pd
import requests
import pdfplumber
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

# =========================================================
#  SYNTHETIC DATA (RFP SCOPE, SKUs, PRICING, TESTS)
# =========================================================

RFP_SCOPE = pd.DataFrame([
    {
        "RFP_ID": "RFP001",
        "Line_No": 1,
        "Description": "3.5C 240 sqmm 1.1kV Al armoured XLPE cable",
        "Voltage_kV": 1.1,
        "Size_sqmm": 240,
        "No_of_Cores": 3.5,
        "Conductor_Material": "Aluminium",
        "Insulation_Type": "XLPE",
        "Armouring_Type": "A1",
        "Quantity_m": 1000,
    },
    {
        "RFP_ID": "RFP001",
        "Line_No": 2,
        "Description": "4C 95 sqmm 1.1kV Cu armoured XLPE cable",
        "Voltage_kV": 1.1,
        "Size_sqmm": 95,
        "No_of_Cores": 4,
        "Conductor_Material": "Copper",
        "Insulation_Type": "XLPE",
        "Armouring_Type": "A2",
        "Quantity_m": 500,
    },
    {
        "RFP_ID": "RFP001",
        "Line_No": 3,
        "Description": "2C 16 sqmm 1.1kV Cu PVC cable",
        "Voltage_kV": 1.1,
        "Size_sqmm": 16,
        "No_of_Cores": 2,
        "Conductor_Material": "Copper",
        "Insulation_Type": "PVC",
        "Armouring_Type": "None",
        "Quantity_m": 2000,
    },
])

SKU_MASTER = pd.DataFrame([
    {
        "SKU_ID": "SKU001",
        "Product_Name": "3.5C 240 sqmm 1.1kV Al XLPE A1",
        "Voltage_Rating_kV": 1.1,
        "Conductor_Size_sqmm": 240,
        "No_of_Cores": 3.5,
        "Conductor_Material": "Aluminium",
        "Insulation_Type": "XLPE",
        "Armouring_Type": "A1",
    },
    {
        "SKU_ID": "SKU002",
        "Product_Name": "4C 240 sqmm 1.1kV Al XLPE A1",
        "Voltage_Rating_kV": 1.1,
        "Conductor_Size_sqmm": 240,
        "No_of_Cores": 4,
        "Conductor_Material": "Aluminium",
        "Insulation_Type": "XLPE",
        "Armouring_Type": "A1",
    },
    {
        "SKU_ID": "SKU003",
        "Product_Name": "4C 95 sqmm 1.1kV Cu XLPE A2",
        "Voltage_Rating_kV": 1.1,
        "Conductor_Size_sqmm": 95,
        "No_of_Cores": 4,
        "Conductor_Material": "Copper",
        "Insulation_Type": "XLPE",
        "Armouring_Type": "A2",
    },
    {
        "SKU_ID": "SKU004",
        "Product_Name": "2C 16 sqmm 1.1kV Cu PVC Non-armoured",
        "Voltage_Rating_kV": 1.1,
        "Conductor_Size_sqmm": 16,
        "No_of_Cores": 2,
        "Conductor_Material": "Copper",
        "Insulation_Type": "PVC",
        "Armouring_Type": "None",
    },
    {
        "SKU_ID": "SKU005",
        "Product_Name": "2C 10 sqmm 1.1kV Cu PVC Non-armoured",
        "Voltage_Rating_kV": 1.1,
        "Conductor_Size_sqmm": 10,
        "No_of_Cores": 2,
        "Conductor_Material": "Copper",
        "Insulation_Type": "PVC",
        "Armouring_Type": "None",
    },
])

SKU_PRICING = pd.DataFrame([
    {
        "SKU_ID": "SKU001",
        "Base_Price_per_meter": 250,
        "Material_Surcharge_per_meter": 30,
        "Packaging_Cost_per_meter": 5,
        "Region_Factor_West": 1.0,
    },
    {
        "SKU_ID": "SKU003",
        "Base_Price_per_meter": 400,
        "Material_Surcharge_per_meter": 40,
        "Packaging_Cost_per_meter": 5,
        "Region_Factor_West": 1.0,
    },
    {
        "SKU_ID": "SKU004",
        "Base_Price_per_meter": 80,
        "Material_Surcharge_per_meter": 10,
        "Packaging_Cost_per_meter": 3,
        "Region_Factor_West": 1.0,
    },
    {
        "SKU_ID": "SKU005",
        "Base_Price_per_meter": 60,
        "Material_Surcharge_per_meter": 8,
        "Packaging_Cost_per_meter": 3,
        "Region_Factor_West": 1.0,
    },
])

TEST_PRICING = pd.DataFrame([
    {
        "Test_ID": "T001",
        "Test_Name": "Type Test as per IS 7098",
        "Applicable_Category": "1.1kV cable",
        "Cost_per_Test": 50000,
    },
    {
        "Test_ID": "T002",
        "Test_Name": "Routine Test",
        "Applicable_Category": "1.1kV cable",
        "Cost_per_Test": 15000,
    },
    {
        "Test_ID": "T003",
        "Test_Name": "Acceptance Test",
        "Applicable_Category": "1.1kV cable",
        "Cost_per_Test": 20000,
    },
])

PLANT_CAPACITY_M_PER_RFP = 5000  # simple capacity assumption


# =========================================================
#  SALES AGENT
# =========================================================

class SalesAgent:
    def __init__(self, horizon_days=90):
        self.horizon_days = horizon_days

    def _fetch_text(self, url: str) -> str:
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            if url.lower().endswith(".pdf"):
                with open("temp_tender.pdf", "wb") as f:
                    f.write(resp.content)
                text = ""
                with pdfplumber.open("temp_tender.pdf") as pdf:
                    for p in pdf.pages:
                        text += p.extract_text() or ""
                return text
            else:
                soup = BeautifulSoup(resp.text, "html.parser")
                return soup.get_text(separator="\n")
        except Exception:
            return ""

    def _extract_due_date(self, text: str):
        patterns = re.findall(r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})", text)
        candidates = []
        for d in patterns:
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
                try:
                    candidates.append(datetime.strptime(d, fmt))
                    break
                except ValueError:
                    continue
        if not candidates:
            return None
        today = datetime.today()
        future = [d for d in candidates if d.date() >= today.date()]
        return min(future) if future else max(candidates)

    def _classify_category(self, text: str) -> str:
        t = text.lower()
        if "cable" in t or "lt cable" in t or "ht cable" in t:
            return "Cables"
        if "wire" in t or "wiring" in t:
            return "Wires"
        if "fan" in t or "switch" in t or "lighting" in t:
            return "FMEG"
        if "paint" in t or "coating" in t:
            return "Paint"
        return "Other"

    def _priority_score(self, days_left, category, idx):
        cat_weight = {
            "Cables": 1.0,
            "Wires": 0.9,
            "FMEG": 0.8,
            "Paint": 0.7,
            "Other": 0.6,
        }.get(category, 0.6)

        if days_left is None:
            time_score = 0.6
        elif days_left <= 30:
            time_score = 1.0
        elif days_left <= 60:
            time_score = 0.8
        else:
            time_score = 0.6

        rev_score = max(0.6, 1.0 - 0.1 * (idx - 1))
        score = 0.5 * time_score + 0.3 * cat_weight + 0.2 * rev_score
        return round(score, 2)

    def _priority_label(self, score):
        if score >= 0.85:
            return "High"
        elif score >= 0.7:
            return "Medium"
        return "Low"

    def run(self, urls):
        rows = []
        today = datetime.today()
        cutoff = today + timedelta(days=self.horizon_days)

        for idx, url in enumerate(urls, start=1):
            text = self._fetch_text(url)
            due_date = self._extract_due_date(text) if text.strip() else None

            # DEMO fallback: future date if missing or past
            if due_date is None or due_date.date() <= today.date():
                offset_days = 30 + (idx - 1) * 10
                if offset_days > self.horizon_days:
                    offset_days = self.horizon_days - 5
                due_date = today + timedelta(days=offset_days)

            category = self._classify_category(text if text.strip() else "")
            days_left = (due_date.date() - today.date()).days
            within_90 = (today.date() <= due_date.date() <= cutoff.date())

            priority_score = self._priority_score(days_left, category, idx)
            priority_label = self._priority_label(priority_score)

            rows.append({
                "RFP_ID": f"LIVE{idx}",
                "RFP_URL": url,
                "Category": category,
                "Submission_Deadline": due_date.date().isoformat(),
                "Days_Left": days_left,
                "Is_Within_90_Days": within_90,
                "Priority_Score": priority_score,
                "Priority_Label": priority_label,
            })

        df = pd.DataFrame(rows)
        eligible = df[df["Is_Within_90_Days"] == True]

        if not eligible.empty:
            selected = eligible.sort_values(
                by=["Priority_Score", "Days_Left"],
                ascending=[False, True]
            ).iloc[0]
        else:
            selected = df.iloc[0]

        return df, eligible, selected.to_dict()


# =========================================================
#  TECHNICAL AGENT
# =========================================================

class TechnicalAgent:
    def __init__(self, rfp_scope_df: pd.DataFrame, sku_master_df: pd.DataFrame):
        self.rfp_scope = rfp_scope_df.copy()
        self.sku_master = sku_master_df.copy()

    def _spec_match_score(self, rfp_line, sku_row):
        score = 0
        total_specs = 6

        try:
            if abs(float(sku_row["Voltage_Rating_kV"]) - float(rfp_line["Voltage_kV"])) <= 0.1:
                score += 1
        except Exception:
            pass

        try:
            sku_size = float(sku_row["Conductor_Size_sqmm"])
            rfp_size = float(rfp_line["Size_sqmm"])
            if rfp_size * 0.9 <= sku_size <= rfp_size * 1.1:
                score += 1
        except Exception:
            pass

        try:
            if float(sku_row["No_of_Cores"]) == float(rfp_line["No_of_Cores"]):
                score += 1
        except Exception:
            pass

        if str(sku_row["Conductor_Material"]).strip().lower() == str(rfp_line["Conductor_Material"]).strip().lower():
            score += 1

        if str(sku_row["Insulation_Type"]).strip().lower() == str(rfp_line["Insulation_Type"]).strip().lower():
            score += 1

        if str(sku_row["Armouring_Type"]).strip().lower() == str(rfp_line["Armouring_Type"]).strip().lower():
            score += 1

        return round((score / total_specs) * 100, 1)

    def top3_for_rfp(self, rfp_id: str):
        rfp_lines = self.rfp_scope[self.rfp_scope["RFP_ID"] == rfp_id]
        if rfp_lines.empty:
            raise ValueError(f"No scope lines found for RFP_ID={rfp_id}")

        all_top3_rows = []
        best_per_line_rows = []

        for _, rfp_line in rfp_lines.iterrows():
            scores = []
            for _, sku_row in self.sku_master.iterrows():
                spec_pct = self._spec_match_score(rfp_line, sku_row)
                scores.append({
                    "RFP_ID": rfp_line["RFP_ID"],
                    "Line_No": rfp_line["Line_No"],
                    "RFP_Description": rfp_line["Description"],
                    "SKU_ID": sku_row["SKU_ID"],
                    "Product_Name": sku_row["Product_Name"],
                    "Spec_Match_%": spec_pct,
                })

            scores_df = pd.DataFrame(scores).sort_values("Spec_Match_%", ascending=False).reset_index(drop=True)
            top3_df = scores_df.head(3)
            all_top3_rows.extend(top3_df.to_dict(orient="records"))
            best_per_line_rows.append(top3_df.iloc[0].to_dict())

        top3_all_lines_df = pd.DataFrame(all_top3_rows)
        best_per_line_df = pd.DataFrame(best_per_line_rows)
        return top3_all_lines_df, best_per_line_df


# =========================================================
#  PRICING AGENT
# =========================================================

class PricingAgent:
    def __init__(self, sku_pricing_df: pd.DataFrame, test_pricing_df: pd.DataFrame):
        self.sku_pricing = sku_pricing_df.copy()
        self.test_pricing = test_pricing_df.copy()

    def get_unit_price(self, sku_id, region="West"):
        row = self.sku_pricing[self.sku_pricing["SKU_ID"] == sku_id]
        if row.empty:
            raise ValueError(f"No pricing found for SKU_ID={sku_id}")
        row = row.iloc[0]
        base = float(row["Base_Price_per_meter"])
        surcharge = float(row["Material_Surcharge_per_meter"])
        packaging = float(row["Packaging_Cost_per_meter"])
        factor = float(row.get("Region_Factor_West", 1.0))
        return round((base + surcharge + packaging) * factor, 2)

    def get_total_test_cost(self):
        total = self.test_pricing["Cost_per_Test"].sum()
        names = self.test_pricing["Test_Name"].tolist()
        return round(total, 2), names

    def price_rfp(self, rfp_scope_df: pd.DataFrame, best_sku_df: pd.DataFrame):
        rows = []
        total_material_cost = 0.0
        total_qty = 0.0

        for _, best_row in best_sku_df.iterrows():
            rfp_id = best_row["RFP_ID"]
            line_no = best_row["Line_No"]
            sku_id = best_row["SKU_ID"]
            spec_match = best_row["Spec_Match_%"]

            qty_row = rfp_scope_df[(rfp_scope_df["RFP_ID"] == rfp_id) &
                                   (rfp_scope_df["Line_No"] == line_no)].iloc[0]
            qty_m = float(qty_row["Quantity_m"])
            total_qty += qty_m

            unit_price = self.get_unit_price(sku_id)
            line_cost = round(unit_price * qty_m, 2)
            total_material_cost += line_cost

            rows.append({
                "RFP_ID": rfp_id,
                "Line_No": line_no,
                "SKU_ID": sku_id,
                "Quantity_m": qty_m,
                "Unit_Price_per_meter": unit_price,
                "Line_Material_Cost": line_cost,
                "Spec_Match_%": spec_match,
            })

        pricing_lines_df = pd.DataFrame(rows)
        total_test_cost, test_names = self.get_total_test_cost()
        total_project_cost = round(total_material_cost + total_test_cost, 2)

        capacity_flag = "Within Capacity" if total_qty <= PLANT_CAPACITY_M_PER_RFP else "Capacity Risk"

        summary = {
            "Total_Material_Cost": round(total_material_cost, 2),
            "Total_Test_Cost": total_test_cost,
            "Tests_Used": ", ".join(test_names),
            "Total_Project_Cost": total_project_cost,
            "Total_Quantity_m": total_qty,
            "Capacity_Flag": capacity_flag,
        }
        return pricing_lines_df, summary


# =========================================================
#  MAIN AGENT
# =========================================================

class MainAgent:
    def calculate_win_probability(self, avg_spec_match_pct, price_competitiveness="Medium", submitted_on_time=True):
        spec_score = avg_spec_match_pct / 100.0
        if price_competitiveness == "High":
            price_score = 1.0
        elif price_competitiveness == "Medium":
            price_score = 0.8
        else:
            price_score = 0.5
        time_score = 1.0 if submitted_on_time else 0.5
        win_prob = (0.5 * spec_score + 0.3 * price_score + 0.2 * time_score) * 100
        return round(win_prob, 1)

    def final_decision(self, win_probability):
        if win_probability >= 70:
            return "✅ GO"
        elif win_probability >= 50:
            return "⚠ REVIEW"
        return "❌ NO-GO"

    def _risk_flag(self, tech, price_share, days_left):
        if tech >= 85:
            tech_risk = "Low"
        elif tech >= 70:
            tech_risk = "Medium"
        else:
            tech_risk = "High"

        if price_share <= 0.1:
            price_risk = "Low"
        elif price_share <= 0.2:
            price_risk = "Medium"
        else:
            price_risk = "High"

        if days_left is None:
            time_risk = "Medium"
        elif days_left >= 21:
            time_risk = "Low"
        elif days_left >= 7:
            time_risk = "Medium"
        else:
            time_risk = "High"

        risks = [tech_risk, price_risk, time_risk]
        if "High" in risks:
            overall = "High"
        elif risks.count("Medium") >= 2:
            overall = "Medium"
        else:
            overall = "Low"

        return tech_risk, price_risk, time_risk, overall

    def build_final_rfp_response(
        self,
        selected_rfp_row,
        rfp_scope_df,
        best_sku_df,
        pricing_lines_df,
        pricing_summary,
        price_competitiveness="Medium"
    ):
        final_lines = rfp_scope_df.merge(
            best_sku_df[["RFP_ID", "Line_No", "SKU_ID", "Spec_Match_%"]],
            on=["RFP_ID", "Line_No"],
            how="left"
        ).merge(
            pricing_lines_df[["RFP_ID", "Line_No", "Unit_Price_per_meter", "Line_Material_Cost"]],
            on=["RFP_ID", "Line_No"],
            how="left"
        )

        final_response_table = final_lines[[
            "RFP_ID",
            "Line_No",
            "Description",
            "SKU_ID",
            "Spec_Match_%",
            "Quantity_m",
            "Unit_Price_per_meter",
            "Line_Material_Cost",
        ]]

        avg_spec = round(best_sku_df["Spec_Match_%"].mean(), 2)
        win_prob = self.calculate_win_probability(
            avg_spec_match_pct=avg_spec,
            price_competitiveness=price_competitiveness,
            submitted_on_time=True
        )
        decision = self.final_decision(win_prob)

        test_share = pricing_summary["Total_Test_Cost"] / pricing_summary["Total_Project_Cost"]
        days_left = selected_rfp_row.get("Days_Left", None)
        tech_risk, price_risk, time_risk, overall_risk = self._risk_flag(avg_spec, test_share, days_left)

        management_summary = {
            "RFP_ID": selected_rfp_row["RFP_ID"],
            "Submission_Deadline": selected_rfp_row["Submission_Deadline"],
            "Category": selected_rfp_row["Category"],
            "Priority_Label": selected_rfp_row.get("Priority_Label", "NA"),
            "Average_Spec_Match_%": avg_spec,
            "Total_Material_Cost": pricing_summary["Total_Material_Cost"],
            "Total_Test_Cost": pricing_summary["Total_Test_Cost"],
            "Total_Project_Cost": pricing_summary["Total_Project_Cost"],
            "Total_Quantity_m": pricing_summary["Total_Quantity_m"],
            "Capacity_Flag": pricing_summary["Capacity_Flag"],
            "Win_Probability_%": win_prob,
            "Final_Decision": decision,
            "Technical_Risk": tech_risk,
            "Commercial_Risk": price_risk,
            "Timeline_Risk": time_risk,
            "Overall_Risk": overall_risk,
        }
        return final_response_table, management_summary


# =========================================================
#  STREAMLIT – GUIDED MULTI-STEP UI
# =========================================================

st.set_page_config(
    page_title="Asian Paints – Agentic RFP Console",
    page_icon="🎨",
    layout="wide"
)

# --- CSS for prettier UI ---
st.markdown("""
    <style>
    .main {
        background: radial-gradient(circle at top left, #ffe4d4 0, #f6f6ff 40%, #ffffff 100%);
    }
    .as-header {
        background: linear-gradient(90deg, #ff6f61, #ffcc33);
        padding: 18px 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 18px;
    }
    .as-tag {
        display:inline-block;
        padding: 2px 9px;
        border-radius: 999px;
        background-color: rgba(255,255,255,0.2);
        font-size: 0.8rem;
        margin-right: 6px;
    }
    .as-section {
        background-color: white;
        padding: 16px 18px;
        border-radius: 14px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.04);
        margin-bottom: 18px;
    }
    .step-chip {
        display:inline-block;
        padding: 6px 14px;
        border-radius: 999px;
        margin-right: 8px;
        font-size: 0.85rem;
        border: 1px solid #ddd;
        background-color: #ffffffaa;
    }
    .step-chip.active {
        background: linear-gradient(90deg, #ff6f61, #ffcc33);
        color: white;
        border-color: transparent;
        font-weight: 600;
    }
    .stButton>button {
        border-radius: 999px;
        padding: 0.4rem 1.3rem;
        border: none;
        background: linear-gradient(90deg, #ff6f61, #ffcc33);
        color: white;
        font-weight: 600;
    }
    .stButton>button:hover {
        filter: brightness(1.05);
    }
    </style>
""", unsafe_allow_html=True)

# ---- Initialize navigation state ----
if "page" not in st.session_state:
    st.session_state["page"] = "overview"

# ---- Header with Asian Paints logo from URL ----
with st.container():
    st.markdown('<div class="as-header">', unsafe_allow_html=True)
    header_cols = st.columns([4, 2])
    with header_cols[0]:
        st.markdown("### 🎨 Asian Paints – AI Tender Command Centre")
        st.markdown(
            '<span class="as-tag">Agentic AI</span>'
            '<span class="as-tag">RFP Automation</span>'
            '<span class="as-tag">Wires • Cables • FMEG</span>',
            unsafe_allow_html=True
        )
    with header_cols[1]:
        st.image(
            "https://static.asianpaints.com/etc.clientlibs/apcolourcatalogue/clientlibs/clientlib-global-unification/resources/images/header/asian-paints-logo.webp",
            use_container_width=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ---- Simple step chips ----
steps = ["overview", "sales", "technical", "pricing"]
labels = {
    "overview": "Overview",
    "sales": "Step 1 – Sales",
    "technical": "Step 2 – Technical",
    "pricing": "Step 3 – Pricing & Decision",
}
current = st.session_state["page"]

chips_html = ""
for s in steps:
    cls = "step-chip active" if s == current else "step-chip"
    chips_html += f'<span class="{cls}">{labels[s]}</span>'
st.markdown(chips_html, unsafe_allow_html=True)
st.markdown("")

# =============== PAGE: OVERVIEW ===============
if current == "overview":
    with st.container():
        st.markdown('<div class="as-section">', unsafe_allow_html=True)
        st.subheader("Why this console exists")
        st.write(
            "- Auto-discovers live tenders from PSU / EPC websites\n"
            "- Translates messy PDFs into structured product requirements\n"
            "- Matches RFP specs to Asian Paints SKUs using a Spec-Match metric\n"
            "- Builds project pricing including material + test cost\n"
            "- Gives a management-grade **Win Probability & GO / NO-GO** recommendation"
        )

        colA, colB, colC = st.columns(3)
        with colA:
            st.metric("Agents", "4", "Sales • Technical • Pricing • Main")
        with colB:
            st.metric("Response Speed", "Minutes", "vs days today")
        with colC:
            st.metric("Target Use", "B2B RFPs", "Infra / PSU / EPC")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Next ▶ Go to Step 1 – Tender Discovery"):
        st.session_state["page"] = "sales"

# =============== PAGE: SALES ===============
elif current == "sales":
    st.markdown('<div class="as-section">', unsafe_allow_html=True)
    st.subheader("Step 1 – Sales Agent: Scan & Prioritise Tenders")

    default_urls = """https://cotcorp.org.in/WriteReadData/Downloads/52%2000%208998TenderNotice10092025.pdf
https://ntpctender.ntpc.co.in/Uploads/job_42677.pdf
https://www.cipet.gov.in/tender-notice/downloads/04-12-2018-001/TENDER_DOCUMENT_FOR_Modular_kitchen.pdf
https://nirdpr.org.in/NIRD_Docs/tenders/tend190117.pdf
"""
    urls_text = st.text_area("Paste tender URLs (one per line):", value=default_urls, height=140)
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]

    if st.button("🚀 Run Sales Agent"):
        if not urls:
            st.error("Please paste at least one tender URL.")
        else:
            sales_agent = SalesAgent(horizon_days=90)
            df_all, df_eligible, selected_rfp_dict = sales_agent.run(urls)

            st.session_state["sales_all"] = df_all
            st.session_state["sales_eligible"] = df_eligible
            st.session_state["selected_rfp"] = selected_rfp_dict

            col1, col2 = st.columns([2, 1.4])
            with col1:
                st.write("📄 All detected RFPs")
                st.dataframe(df_all, use_container_width=True)
            with col2:
                st.write("✅ RFPs in 90-day response window")
                st.dataframe(df_eligible, use_container_width=True)

            st.success(
                f"Selected RFP for pipeline: **{selected_rfp_dict['RFP_ID']}**  | "
                f"Category: {selected_rfp_dict['Category']}  | "
                f"Priority: {selected_rfp_dict['Priority_Label']}"
            )

    st.markdown("</div>", unsafe_allow_html=True)

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅ Back to Overview"):
            st.session_state["page"] = "overview"
    with col_next:
        if st.button("Next ▶ Go to Step 2 – Technical Matching"):
            st.session_state["page"] = "technical"

# =============== PAGE: TECHNICAL ===============
elif current == "technical":
    st.markdown('<div class="as-section">', unsafe_allow_html=True)
    st.subheader("Step 2 – Technical Agent: Spec-Match & SKU Recommendation")

    if "selected_rfp" not in st.session_state:
        st.info("Run **Step 1 – Tender Discovery** first to select an RFP.")
    else:
        selected_rfp = st.session_state["selected_rfp"]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Selected RFP", selected_rfp["RFP_ID"])
        with c2:
            st.metric("Category", selected_rfp["Category"])
        with c3:
            st.metric("AI Priority", selected_rfp.get("Priority_Label", "NA"))

        if st.button("🧪 Run Technical Agent"):
            rfp_id = selected_rfp["RFP_ID"]
            RFP_SCOPE_ACTIVE = RFP_SCOPE.copy()
            RFP_SCOPE_ACTIVE["RFP_ID"] = rfp_id

            tech_agent = TechnicalAgent(RFP_SCOPE_ACTIVE, SKU_MASTER)
            tech_top3_df, best_sku_per_line_df = tech_agent.top3_for_rfp(rfp_id)

            st.session_state["rfp_scope_active"] = RFP_SCOPE_ACTIVE
            st.session_state["tech_top3"] = tech_top3_df
            st.session_state["best_sku_per_line"] = best_sku_per_line_df

            st.write("📦 Scope of supply detected from RFP")
            st.dataframe(RFP_SCOPE_ACTIVE, use_container_width=True)

            st.write("🏆 Top-3 SKUs per line with Spec-Match%")
            st.dataframe(tech_top3_df, use_container_width=True)

            st.write("✅ Recommended SKU per line (goes to Pricing)")
            st.dataframe(best_sku_per_line_df, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅ Back to Step 1"):
            st.session_state["page"] = "sales"
    with col_next:
        if st.button("Next ▶ Go to Step 3 – Pricing & Decision"):
            st.session_state["page"] = "pricing"

# =============== PAGE: PRICING ===============
elif current == "pricing":
    st.markdown('<div class="as-section">', unsafe_allow_html=True)
    st.subheader("Step 3 – Pricing & Main Agent: Bid Costing & Decision")

    if "best_sku_per_line" not in st.session_state or "selected_rfp" not in st.session_state:
        st.info("Run **Step 2 – Technical Matching** first.")
    else:
        if st.button("💰 Run Pricing & Decision Agents"):
            RFP_SCOPE_ACTIVE = st.session_state["rfp_scope_active"]
            best_sku_per_line_df = st.session_state["best_sku_per_line"]
            selected_rfp = st.session_state["selected_rfp"]

            pricing_agent = PricingAgent(SKU_PRICING, TEST_PRICING)
            pricing_lines_df, pricing_summary = pricing_agent.price_rfp(
                rfp_scope_df=RFP_SCOPE_ACTIVE,
                best_sku_df=best_sku_per_line_df
            )

            main_agent = MainAgent()
            final_response_table, management_summary = main_agent.build_final_rfp_response(
                selected_rfp_row=selected_rfp,
                rfp_scope_df=RFP_SCOPE_ACTIVE,
                best_sku_df=best_sku_per_line_df,
                pricing_lines_df=pricing_lines_df,
                pricing_summary=pricing_summary,
                price_competitiveness="Medium"
            )

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Win Probability", f"{management_summary['Win_Probability_%']}%")
            with k2:
                st.metric("Total Project Cost", f"₹ {management_summary['Total_Project_Cost']:.0f}")
            with k3:
                st.metric("Overall Risk", management_summary["Overall_Risk"])
            with k4:
                st.metric("AI Decision", management_summary["Final_Decision"])

            st.write("💵 Line-wise costing (Pricing Agent)")
            st.dataframe(pricing_lines_df, use_container_width=True)

            st.write("📊 Final RFP response table (what Sales submits)")
            st.dataframe(final_response_table, use_container_width=True)

            st.write("🧠 Management view – extended summary")
            st.dataframe(pd.DataFrame([management_summary]), use_container_width=True)

            st.success(
                f"Recommendation: {management_summary['Final_Decision']}  | "
                f"Win Probability: {management_summary['Win_Probability_%']}%  | "
                f"Capacity: {management_summary['Capacity_Flag']}  | "
                f"Risk: {management_summary['Overall_Risk']}"
            )

    st.markdown("</div>", unsafe_allow_html=True)

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅ Back to Step 2"):
            st.session_state["page"] = "technical"
    with col_next:
        if st.button("🏁 Back to Overview"):
            st.session_state["page"] = "overview"


# In[ ]:




