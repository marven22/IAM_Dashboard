import streamlit as st
import json
import os
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import pathlib

# =============================
# Load Precomputed Results
# =============================
# Dynamically resolve the folder containing precomputed results
BASE_DIR = pathlib.Path(__file__).parent
RESULTS_DIR = BASE_DIR

def load_iteration_data():
    results = {}
    for fname in sorted(os.listdir(RESULTS_DIR)):
        if fname.startswith("iteration_") and fname.endswith(".json"):
            with open(os.path.join(RESULTS_DIR, fname), "r") as f:
                data = json.load(f)
                results[data["iteration"]] = data
    return results

def load_final_dashboard():
    with open(os.path.join(RESULTS_DIR, "final_dashboard.json"), "r") as f:
        return json.load(f)

iteration_results = load_iteration_data()
final_dashboard = load_final_dashboard()

# =============================
# Streamlit UI
# =============================
st.set_page_config(page_title="IAM Policy POC", layout="wide")
st.title("🔒 Self-Verifying Intelligence: IAM Policy POC")
st.markdown("This demo showcases how **LLM-guided automated reasoning** evolves contracts, repairs IAM policies, and produces proof-carrying artifacts.")

# Sidebar navigation
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Iteration Explorer", "Results Dashboard"]
)

# =============================
# Page 1: Overview
# =============================
if page == "Overview":
    st.header("Overview")
    st.write("""
    - **Goal**: Demonstrate automated reasoning for IAM policies using contracts, LLM-guided repairs, and proof-carrying diffs.
    - **Method**: 
        - LLM Challenger proposes adversarial mutations.
        - Proof system checks violations.
        - LLM Repairs suggest safer policies.
        - Contracts evolve and validate.
    - **Results**: Reviewers can explore precomputed runs (10 iterations) and compare baseline vs POC outcomes.
    """)
    col1, col2 = st.columns(2)
    col1.metric("Total Iterations Run", len(iteration_results))
    col2.metric("Evolved Contracts", len(final_dashboard.get("evolved_contracts", [])))

# =============================
# Page 2: Iteration Explorer
# =============================
elif page == "Iteration Explorer":
    st.header("🔍 Iteration Explorer")
    st.markdown("""
    Explore each iteration — from **LLM mutation** → **formal proof validation (Lean/Dafny)** → **policy repair** → **CST safety improvement**.
    """)

    iteration = st.selectbox("Select iteration:", list(iteration_results.keys()))
    data = iteration_results[iteration]
    cst = data.get("cst_results", {})

    before_rate = cst.get("before", {}).get("violation_rate", 0)
    after_rate = cst.get("after", {}).get("violation_rate", 0)
    reduction = cst.get("violation_reduction", 0)

    # ======= Summary Capsule =======
    html = f"""
    <div style='background:linear-gradient(90deg,#0f2027,#203a43,#2c5364);
    color:white;padding:1em;border-radius:10px;font-size:0.9em;line-height:1.5em;'>
      <b>Iteration {iteration}</b><br>
      <b>Mutation:</b> {data['mutation_meta'].get('desc')} 
      <span style='opacity:0.6'>({data['mutation_meta'].get('source')})</span><br>
      ⚙️ <b>Contracts:</b> {len(data['proof']['strict_mode'])} |
      ❌ <b>Failures:</b> {sum(1 for v in data['proof']['strict_mode'].values() if v.startswith('FAIL'))}<br>
      📉 <b>Violation Rate:</b> {before_rate:.3f} → {after_rate:.3f} |
      🧩 <b>Δ (Reduction):</b> {reduction:.3f}
    </div>
    """
    import streamlit.components.v1 as components
    components.html(html, height=180)

    st.markdown("---")

    # ======================
    # 🧨 Broken (Mutated) Policy
    # ======================
    st.subheader("🧨 Mutated Policy (Broken)", 
                 help="This is the IAM policy after the LLM challenger introduced a mutation. It typically violates one or more security contracts.")
    st.caption("These mutations mimic real-world misconfigurations such as missing MFA, wildcards, or cross-service privileges.")
    st.json(data.get("mutated_policy", {}))

    st.markdown("---")

    # ======= Proof Results =======
    st.subheader("📜 Proof Results (Strict Mode)", 
        help="Formal verification results from contract-based analysis. "
             "'FAIL' indicates a contract violation; 'PASS' means the policy satisfies the safety invariant.")
    st.caption("Each contract is a logical rule (e.g., 'no wildcards', 'no privilege escalation', 'resource containment').")
    st.json(data["proof"]["strict_mode"])

    # ======= Exploratory Mode =======
    st.subheader("🧠 Exploratory Mode", 
        help="Soft reasoning layer: provides advisory suggestions when a policy is borderline unsafe.")
    st.caption("Helps bridge formal proofs with heuristic refinement — similar to an AI auditor’s recommendations.")
    st.json(data["proof"]["exploratory_mode"])

    # ======= Lean and Dafny Proof Exports =======
    st.markdown("### 🧾 Formal Proof Artifacts (Lean & Dafny)")
    st.caption("These are the *actual theorems and lemmas* exported for each iteration. "
               "They correspond to the same contracts listed above, serving as formal certificates of policy safety.")

    with st.expander("📘 Lean Theorems", expanded=False):
        st.code(data.get("lean_export", ""), language="lean")

    with st.expander("🔷 Dafny Lemmas", expanded=False):
        st.code(data.get("dafny_export", ""), language="dafny")

    st.markdown("""
    ✅ **Interpretation:**  
    - Each `theorem` or `lemma` corresponds to a contract.  
    - If the Lean theorem ends with `:= by sorry`, it means the proof failed (violation).  
    - Dafny lemmas that include `assert false; // violation` represent unsafe statements.  
    - Together, they provide machine-verifiable proofs of compliance or violation.
    """)

    # ======= CST Results =======
    if cst:
        st.subheader("🧩 Request-Level CST Results", 
            help="Monte Carlo-based analysis estimating unsafe-allow probability before and after LLM repair.")
        st.caption("Measures empirical safety improvement by simulating random access requests.")
        st.json(cst)
    else:
        st.info("No CST results found for this iteration.")

    # ======= LLM Repair Suggestions =======
    st.subheader("🪄 LLM Repair Suggestions", 
        help="GPT-generated policy fragments that fix failed contracts while preserving intended access.")
    st.caption("Each fix replaces unsafe elements (e.g., wildcards) with least-privilege statements.")
    repairs = data["proof"].get("repair_suggestions", {})
    if repairs:
        for cname, suggestion in repairs.items():
            with st.expander(f"💡 Fix for {cname}"):
                st.code(suggestion, language="json")
    else:
        st.info("No repair suggestions generated in this iteration.")

    # ======= Repaired Policy =======
    st.subheader("🛡️ Repaired Policy", 
        help="Final IAM policy after applying LLM-suggested fixes.")
    st.caption("This version should satisfy all contracts and form a proof-carrying artifact.")
    st.json(data["repaired_policy"])

    # ======= LLM Explanation =======
    st.subheader("🧠 LLM Explanation of Proof Failures", 
        help="Natural-language summary derived from Lean/Dafny proofs, explaining why formal checks failed.")
    st.caption("Links the formal reasoning layer with intuitive security semantics for human reviewers.")
    st.write(data.get("llm_explanation", "No explanation available."))
# =============================
# Page 3: Final Dashboard (Redesigned)
# =============================
elif page == "Results Dashboard":
    st.header("📊 Final Dashboard Summary")

    # --- Evolved Contracts ---
    st.subheader("🧬 Evolved Contracts",
        help="Lists all IAM verification contracts that were active at the end of the run, "
             "including both preloaded (archive-seed) and LLM-induced rules.")
    if final_dashboard["evolved_contracts"]:
        st.success(", ".join(final_dashboard["evolved_contracts"]))
    else:
        st.warning("No contracts evolved in this run.")

    col1, col2 = st.columns(2)


    # --- Contract Provenance Visualization (Augmented) ---
    st.subheader("🧬 Contract Provenance, Origins, and Promotion Status", 
        help="Shows where each contract came from (seed vs GPT), "
             "when it first appeared, and whether it’s fully promoted or still a candidate.")

    provenance_rows = []
    meta = final_dashboard.get("contract_metadata", {})
    evolved = set(final_dashboard.get("evolved_contracts", []))
    candidates = set(final_dashboard.get("candidate_contracts", []))

    # Build provenance table with promotion status
    all_contracts = set(list(evolved) + list(candidates) + list(meta.keys()))
    for cname in sorted(all_contracts):
        origin = meta.get(cname, {}).get("origin", "unknown")
        first_iter = meta.get(cname, {}).get("iteration", "?")

        # Determine readable origin symbol
        if origin == "gpt":
            origin_symbol = "🧠 GPT"
        elif origin == "seed":
            origin_symbol = "⚙️ Seed"
        else:
            origin_symbol = "🔵 Evolved"

        # Determine promotion status
        if cname in evolved:
            status = "✅ Promoted"
        elif origin == "seed":
            status = "⚙️ Stable"
        else:
            status = "⏳ Candidate"

        provenance_rows.append({
            "Contract": cname,
            "Origin": origin_symbol,
            "Promotion Status": status
        })

    if provenance_rows:
        st.dataframe(
            pd.DataFrame(provenance_rows),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No contract metadata available to display provenance.")

    st.markdown("""
    **Legend:**  
    🧠 **GPT** → Discovered autonomously by the LLM  
    ⚙️ **Seed** → Preloaded in the Archive  
    🔵 **Evolved** → Derived through self-learning  
    ✅ **Promoted** → Fully validated and now part of main safety rules  
    ⏳ **Candidate** → Detected but not yet validated  
    """)

    # =================================================================
    # 🔧 Repair Impact Summary (Comprehensive Visualization)
    # =================================================================
    st.subheader("🔧 Repair Impact Summary",
        help=(
            "Shows quantitative improvements in proof satisfaction (Before vs After) "
            "and empirical safety (CST Δ) after LLM-guided policy repairs."
        )
    )

    if final_dashboard.get("repair_improvements") or final_dashboard.get("repair_failures"):
        repair_data = final_dashboard.get("repair_improvements", []) + final_dashboard.get("repair_failures", [])
        rep_df = pd.DataFrame(repair_data, columns=["Iteration", "Before", "After", "CST Δ"]).set_index("Iteration")

        # Compute deltas
        rep_df["Δ Proof Score"] = rep_df["After"] - rep_df["Before"]

        # --- Proof-Level Improvement ---
        st.markdown("#### 🧮 Proof-Level Improvement  " +
            "*(Measures formal proof satisfaction rate across all contracts)*"
        )
        st.caption("Each point shows the fraction of verified contracts before and after LLM repair. Higher is better.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Proof Score (Before)", round(rep_df["Before"].mean(), 3))
        col2.metric("Avg Proof Score (After)", round(rep_df["After"].mean(), 3))
        col3.metric("Avg Δ Proof Score", round(rep_df["Δ Proof Score"].mean(), 3))

        st.line_chart(
            rep_df[["Before", "After"]],
            height=250,
            use_container_width=True
        )


    # =================================================================
    # 📈 Canonical CST Summary (Unified)
    # =================================================================
    st.subheader("📈 Request-Level CST Summary (Canonical)",
        help="Monte Carlo evaluation of policy safety before and after LLM-guided repairs. "
             "Measures the empirical risk of unsafe permissions (lower is better).")

    cs = final_dashboard.get("cst_summary", {})
    if cs and cs.get("avg_before") is not None:
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg Violation Rate (Baseline)", round(cs["avg_before"], 3))
        col2.metric("Avg Violation Rate (After PCR)", round(cs["avg_after"], 3))
        col3.metric("Avg Δ (Reduction)", round(cs["avg_delta"], 3))

        st.line_chart(pd.DataFrame({
            "Baseline Violation Rate": cs["before_rates"],
            "After PCR Violation Rate": cs["after_rates"]
        }), height=250)
    else:
        st.warning("No CST summary available. Regenerate precomputed results.")

    # --- Exports / Proof Stats ---
    st.subheader("📜 Proof Export Stats",
        help="Summary of theorem prover outcomes from Lean and Dafny backends.")
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.metric("Lean Unprovable Theorems", final_dashboard["lean_unprovable"])
    with exp_col2:
        st.metric("Dafny Violations", final_dashboard["dafny_violations"])


