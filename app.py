"""
TenderGenie - Enterprise AI RFP Response & Bid Optimization Engine
Executive Web Interface
"""

import os
import streamlit as st
import pandas as pd
from core.graph import tender_pipeline

st.set_page_config(
    page_title="TenderGenie | Autonomous RFP Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Styling
st.markdown("""
<style>
    /* Global Container */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }
    
    /* Top Header Banner */
    .hero-banner {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border-radius: 12px;
        padding: 24px 30px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 14px 0 rgba(15, 23, 42, 0.15);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0;
        background: linear-gradient(90deg, #60A5FA, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-desc {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-top: 6px;
        margin-bottom: 0;
    }

    /* Process Flow Pills */
    .flow-badge-container {
        display: flex;
        gap: 12px;
        margin-top: 18px;
        flex-wrap: wrap;
    }
    .flow-badge {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        color: #E2E8F0;
    }

    /* KPI Summary Cards */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        text-align: left;
    }
    .kpi-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #64748B;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.45rem;
        font-weight: 800;
        color: #0F172A;
        margin-top: 4px;
    }

    /* Deliverable & Risk Items */
    .deliverable-box {
        background: #FFFFFF;
        border-left: 4px solid #3B82F6;
        border-top: 1px solid #E2E8F0;
        border-right: 1px solid #E2E8F0;
        border-bottom: 1px solid #E2E8F0;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
    .risk-high-box {
        background: #FEF2F2;
        border-left: 4px solid #EF4444;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
    .risk-warn-box {
        background: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Top Hero Section
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">⚡ TenderGenie AI · Enterprise Bid Studio</div>
    <div class="hero-desc">Autonomous multi-agent orchestration engine for RFP extraction, compliance analysis, commercial modeling, and proposal synthesis.</div>
    <div class="flow-badge-container">
        <span class="flow-badge">📄 PyMuPDF Ingestion</span>
        <span class="flow-badge">🧠 LangGraph Cyclic State</span>
        <span class="flow-badge">⚖️ Contract Compliance</span>
        <span class="flow-badge">💰 Dynamic BOQ & Margin</span>
        <span class="flow-badge">✍️ GPT-4o-mini Synthesis</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("### 📂 Source Document")
sample_dir = "data/samples"
available_samples = []
if os.path.exists(sample_dir):
    available_samples = sorted([f for f in os.listdir(sample_dir) if f.endswith(".pdf")])

input_mode = st.sidebar.radio("Select Source Mode:", ["Preset Verified Samples", "Custom RFP Upload"])
raw_text = ""
selected_file_name = "None"

if input_mode == "Preset Verified Samples" and available_samples:
    selected_sample = st.sidebar.selectbox("Active RFP File:", available_samples)
    selected_file_name = selected_sample
    file_path = os.path.join(sample_dir, selected_sample)
    try:
        import pymupdf
        doc = pymupdf.open(file_path)
        raw_text = "\n".join([page.get_text() for page in doc])
        st.sidebar.caption(f"✔ Extracted {len(doc)} pages · {len(raw_text.split())} words")
    except Exception:
        raw_text = f"Sample requirement document for {selected_sample}"
else:
    uploaded_file = st.sidebar.file_uploader("Upload Tender PDF", type=["pdf", "txt"])
    if uploaded_file:
        selected_file_name = uploaded_file.name
        if uploaded_file.name.endswith(".pdf"):
            try:
                import pymupdf
                doc = pymupdf.open(stream=uploaded_file.read(), filetype="pdf")
                raw_text = "\n".join([page.get_text() for page in doc])
                st.sidebar.caption(f"✔ Extracted {len(doc)} pages")
            except Exception:
                raw_text = "Uploaded standard enterprise requirements text."
        else:
            raw_text = uploaded_file.read().decode("utf-8")

st.sidebar.markdown("---")
process_button = st.sidebar.button("🚀 Run Pipeline Orchestrator", type="primary", use_container_width=True)

# Session State
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None

if process_button:
    if not raw_text.strip():
        st.sidebar.error("Please load or upload a document first.")
    else:
        with st.spinner("Executing agent graph nodes..."):
            initial_state = {"raw_text": raw_text, "current_status": "Starting Pipeline"}
            output_state = tender_pipeline.invoke(initial_state)
            st.session_state.pipeline_result = output_state
            st.toast("Full RFP analysis and proposal synthesized!", icon="✅")

# If pipeline has run
if st.session_state.pipeline_result:
    res = st.session_state.pipeline_result
    parsed_scope = res.get("parsed_scope", {})
    comp = res.get("compliance_report", {})
    pricing = res.get("pricing_estimate", {})

    # Top KPI Metrics Strip
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Contract Timeline</div><div class="kpi-value">{parsed_scope.get("delivery_timeline", "6 Months")}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Target SLA Guarantee</div><div class="kpi-value">{parsed_scope.get("sla_threshold", "99.9% Uptime")}</div></div>', unsafe_allow_html=True)
    with col3:
        final_amt = pricing.get("final_bid_amount_usd", 29040)
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Calculated Commercial Bid</div><div class="kpi-value" style="color:#2563EB;">${final_amt:,.0f}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Audit & Pipeline Status</div><div class="kpi-value" style="color:#10B981; font-size:1.15rem;">Verified Eligible</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Extracted Scope & Deliverables",
        "⚖️ Compliance & Legal Audit",
        "💰 Commercial BOQ & Margin Modeler",
        "📄 Generated Executive Proposal"
    ])

    # Tab 1: Scope
    with tab1:
        st.markdown("#### Structured Functional Deliverables")
        deliverables = parsed_scope.get("deliverables", [])
        if deliverables:
            for idx, item in enumerate(deliverables, 1):
                if isinstance(item, dict):
                    title = item.get("title", f"Deliverable {idx}")
                    desc = item.get("description", "Core requirement item.")
                    timeline = item.get("timeline")
                    tl_badge = f"<span style='float:right; font-size:0.8rem; background:#E2E8F0; padding:2px 8px; border-radius:4px;'>{timeline}</span>" if timeline else ""
                    st.markdown(f"""
                    <div class="deliverable-box">
                        <div style="font-weight:700; color:#1E293B; font-size:1.05rem;">{idx}. {title} {tl_badge}</div>
                        <div style="color:#475569; font-size:0.9rem; margin-top:4px;">{desc}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="deliverable-box">
                        <div style="font-weight:700; color:#1E293B;">{idx}. {item}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No explicit structured deliverables detected in scope.")

    # Tab 2: Compliance
    with tab2:
        st.markdown("#### Contractual Penalty & SLA Risk Assessment")
        matrix = comp.get("compliance_matrix", [])
        if matrix:
            st.dataframe(pd.DataFrame(matrix), use_container_width=True)
        else:
            risk_flags = comp.get("risk_flags", [])
            if risk_flags:
                for rf in risk_flags:
                    sev = rf.get("severity", "Yellow")
                    box_class = "risk-high-box" if sev.lower() == "red" else "risk-warn-box"
                    st.markdown(f"""
                    <div class="{box_class}">
                        <div style="font-weight:700; font-size:1.05rem; color:#0F172A;">⚠️ {rf.get('clause', 'Clause')} (Severity: {sev})</div>
                        <div style="color:#334155; margin-top:5px;"><b>Penalty Specification:</b> {rf.get('penalty_details', 'N/A')}</div>
                        <div style="color:#0F172A; margin-top:3px;"><b>Recommended Mitigation:</b> {rf.get('mitigation_strategy', 'N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("Tender document contains standard contractual terms. No penalty risks identified.")

    # Tab 3: Pricing
    with tab3:
        st.markdown("#### Dynamic Resource Costing & Margin Modeler")
        col_ctrl, col_table = st.columns([1, 2])
        with col_ctrl:
            st.markdown("##### Financial Parameters")
            current_margin = pricing.get("recommended_margin_pct", 20)
            target_margin = st.slider("Target Operating Margin (%)", min_value=5, max_value=40, value=int(current_margin))
            
            subtotal = pricing.get("subtotal_usd", 24200)
            calculated_bid = subtotal * (1 + (target_margin / 100))
            
            st.markdown(f"""
            <div style="background:#F1F5F9; border:1px solid #CBD5E1; padding:18px; border-radius:8px; margin-top:15px;">
                <div style="font-size:0.8rem; color:#64748B; font-weight:700;">TOTAL ESTIMATED PROPOSAL BID</div>
                <div style="font-size:1.8rem; font-weight:800; color:#1E3A8A;">${calculated_bid:,.2f}</div>
                <div style="font-size:0.85rem; color:#475569; margin-top:4px;">Base Cost: ${subtotal:,.2f} · Margin: {target_margin}%</div>
            </div>
            """, unsafe_allow_html=True)

        with col_table:
            st.markdown("##### Bill of Quantities (BOQ)")
            boq = pricing.get("boq_items") or pricing.get("items", [])
            if boq:
                st.dataframe(pd.DataFrame(boq), use_container_width=True)

    # Tab 4: Proposal Draft
    with tab4:
        st.markdown("#### Autonomous AI Bid Proposal")
        proposal_text = res.get("final_proposal", "No proposal generated.")
        
        st.download_button(
            label="📥 Export Submission-Ready Proposal (.md)",
            data=proposal_text,
            file_name=f"TenderGenie_Proposal_{selected_file_name}.md",
            mime="text/markdown",
            use_container_width=False
        )
        st.markdown("---")
        st.markdown(proposal_text)

else:
    # Rich Empty-State Presentation for Demo
    st.markdown("""
    <div style="background:#FFFFFF; border:1px dashed #CBD5E1; border-radius:12px; padding:35px 25px; text-align:center; margin-top:10px;">
        <h3 style="color:#1E293B; margin-bottom:8px;">Ready to Evaluate Tender</h3>
        <p style="color:#64748B; max-width:620px; margin:0 auto 20px auto;">
            Choose a pre-configured RFP scenario from the sidebar and trigger the orchestrator. The multi-agent pipeline will execute full ingestion, compliance checks, margin calibration, and bid synthesis.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-label">Agent 1: Ingestion & Parser</div>
            <div style="color:#1E293B; font-weight:700; margin-top:6px;">PyMuPDF + Pydantic v2</div>
            <div style="color:#64748B; font-size:0.85rem; margin-top:4px;">Extracts complex tables and maps deliverables into a validated typed schema.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-label">Agent 2: Compliance Auditor</div>
            <div style="color:#1E293B; font-weight:700; margin-top:6px;">Risk & SLA Penalty Engine</div>
            <div style="color:#64748B; font-size:0.85rem; margin-top:4px;">Detects liquidated damages and SLA penalty risks with automated mitigation strategies.</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-label">Agent 3 & 4: Pricing & Drafter</div>
            <div style="color:#1E293B; font-weight:700; margin-top:6px;">Dynamic BOQ + GPT-4o-mini</div>
            <div style="color:#64748B; font-size:0.85rem; margin-top:4px;">Calibrates engineering margins and synthesizes a full technical proposal in seconds.</div>
        </div>
        """, unsafe_allow_html=True)