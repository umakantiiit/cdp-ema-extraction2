import streamlit as st
import json
import re

# Page configuration
st.set_page_config(
    page_title="EMA Extraction Tool",
    page_icon="🩺",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        display: flex;
        align-items: center;
        gap: 15px;
        padding: 10px 0;
        border-bottom: 2px solid #6C63FF;
        margin-bottom: 30px;
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #6C63FF;
        margin: 0;
    }
    .stethoscope-icon {
        font-size: 2.5rem;
    }
    .json-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #6C63FF;
    }
    .indication-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .indication-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .detail-item {
        background-color: rgba(255, 255, 255, 0.15);
        padding: 8px 12px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 30px;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 25px;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Header with logo and title
col_logo, col_title = st.columns([1, 8])

with col_logo:
    # Display the uploaded logo - place your logo file in the same directory
    try:
        st.image("image.jpg", width=80)
    except:
        st.markdown("🩺", unsafe_allow_html=True)

with col_title:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 2.5rem;">🩺</span>
        <h1 style="color: #6C63FF; margin: 0;">EMA EXTRACTION TOOL</h1>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# CDP EMA Prompt (placeholder - replace with your actual prompt)
cdp_ema_prompt = """
# Role and Persona
You are an expert Clinical Data Analyst and Regulatory Affairs Specialist specializing in Pharmacovigilance. Your expertise lies in parsing complex medical texts from the European Medicines Agency (EMA) and extracting highly structured data with zero error. You do not summarize; you extract exactly what is stated.

# Objective
Your task is to analyze the provided EMA clinical text and convert it into a single valid JSON array. The text contains various "Primary Disease Categories," and within those categories, multiple specific "Indications."

# Extraction Rules (Strict Compliance Required)

## 1. High-Level Logic
- The input text is divided into sections based on disease types (e.g., "Melanoma", "Non-small cell lung cancer").
- For each section, capture the `Disease_level_full_text`. This is the raw text for that entire disease section.
- Within the `Disease_level_full_text`, identify every distinct "Indication".
- Create a separate JSON object for *each* indication found.

## 2. Field-Specific Definitions & Extraction Logic

### **Primary Disease_category**
- **Source:** The bolded or capitalized header starting the section.
- FALLBACK APPROACH - "If no explicit header exists, use the disease name found in the indication text as the Primary Category."
- IF the Indication_text lists multiple distinct tumor types (e.g., "gastric, small intestine, or biliary cancer") that share the same treatment conditions, you MUST create a separate JSON object for each tumor type.
- Bad Example: {"Disease": "gastric, small intestine, or biliary cancer"}
- Good Example: [{"Disease": "gastric cancer"}, {"Disease": "small intestine cancer"}, {"Disease": "biliary cancer"}]
- **Example:** "Melanoma", "Non-small cell lung cancer (NSCLC)".

### **Disease_level_full_text**
- **Source:** The entire text block belonging to that Primary Disease Category.
- **Rule:** This text will repeat identically for every indication object that belongs to this category.

### **Indication #**
- **Logic:** An integer counter (1, 2, 3...) representing the specific indication sequence within that Primary Disease Category. Reset to 1 for a new Disease Category.

### **Indication_text**
- **Source:** The specific sentence(s) defining who and what is being treated.
- **Constraint:** Stop extracting when the text moves to a new patient population or a different drug combination.

### **Treatment line**
- **Source:** EXTRACT ONLY FROM "Indication_text".
- **Logic:**
  - If text says "first-line": value is "First line".
  - If the indication text explicitly contains the words “second-line” or “second line”, output: "Second line".
  - If text says "after prior therapy", "after prior chemotherapy", "after failure of prior therapy", "after failure of platinum therapy", "progressing on or after", "disease progression following", "previously treated with", "relapsed after", "refractory after", "second-line": value is "Second line".
  - If the indication text explicitly contains the words “third-line” or “third line”, output: "Third line".
  - If the indication text clearly indicates two sequential prior treatments, output “Third line”.
  - **Example:**“after autologous stem cell transplant and treatment with …”.
  - **Example:**“after two or more prior therapies”.
  - **Example:**“after both chemotherapy and targeted therapy”.
  - If text mentions "Adjuvant" or "Neoadjuvant" without specifying a line: value is "_".
  - If no line is mentioned: value is "_".
  - Do not convert adjuvant or neoadjuvant into first or second line.
  - Do NOT assign a treatment line based on drug class or clinical knowledge
  - Only the words inside the Indication_text control Treatment line.

    
### **Treatment modality**
- **Source:** EXTRACT ONLY FROM "Indication_text".
- **Logic:** Look for these keywords and combine them with commas if multiple exist:
  - "Monotherapy" (or implied if used alone).
  - "Combination" (if the text contains “in combination with”; if used with ipilimumab, chemotherapy, etc.).
  - "Adjuvant".
  - "Neoadjuvant".
  - If multiple modalities apply, combine them using commas in a single string.
- **Example:** "Combination, Neoadjuvant"

    
### **Population**
- **Source:** EXTRACT ONLY FROM "Indication_text".
- **Logic:** Identify the target demographic.
- Text-based population rules:
  - If the text contains infant, neonate, or newborn, output “Infant”.
  - If the text contains pediatric, paediatric, or children, output “Paediatric”.
  - If the text contains adolescents, output “Adolescent”.
  - If the text contains adults or adult patients, output “Adult”.
  - If the text contains elderly, geriatric, or ≥ 65 years, output “Elderly”.
- Numeric age-based population rules (mandatory):
  - Age 0 to 1 years maps to “Infant”.
  - Age greater than 1 and up to 12 years maps to “Pediatric”.
  - Age greater than 12 and up to 18 years maps to “Adolescent”.
  - Age greater than 18 and up to 60 years maps to “Adult”.
  - Age greater than 60 years maps to “Elderly”.
- Range overlap rules:
  - If an age range spans multiple groups, include all applicable populations.
  - **Example:** Age 10 to 14 outputs “Pediatric, Adolescent”.
  - **Example:** Age 58 to 70 outputs “Adult, Elderly”.
  - **Example:** ≥12 years outputs “Adolescent, Adult, Elderly”.
- Population formatting rules:
  - Only these exact values are allowed:
    - Infant
    - Paediatric
    - Adolescent
    - Adult
    - Elderly
  - If no text age and no numeric age is present, output “_”.
  - Never default to Adult.
  - Never guess the population.

  
**Final Formatting:**
- Join multiple matches with a comma (e.g., "Adult, Adolescent").
- If no population is mentioned, valid output is null or inferred from context only if highly obvious, otherwise "_".

### **Disease + sybtypes**
- **Source:** EXTRACT ONLY FROM "Indication_text".
- **Logic:** Extract the specific condition description, stage, or mutation status mentioned.
- **Example:** "unresectable or metastatic melanoma" or "tumours have PD-L1 expression >= 1%".

Field: Disease + subtypes (Strict Cleaning Rules)
Objective: Extract only the specific medical condition or patient state. Critical Rule: This field describes the PATIENT'S BODY, not the DRUG'S ACTION.

Instructions to extract text for Disease+subtypes:

Start by identifying the core disease name (e.g., "Type 2 diabetes mellitus", "Melanoma").

Keep specific disease modifiers found immediately around the disease name:

"insufficiently controlled"

"metastatic", "advanced", "resectable", "unresectable"

Specific genetic mutations (e.g., "PD-L1 positive", "BRAF V600 mutation")

Risk levels (e.g., "at high risk of recurrence")

REMOVE all text related to:

Treatment Context: "as an adjunct to diet and exercise", "in combination with...", "as monotherapy".

Rationale/Reasoning: "when metformin is considered inappropriate", "due to intolerance".

Treatment History (unless part of the patient definition): "after failure of...", "progressing on...". ( Note: Only keep these if they define the patient group, like 'relapsed/refractory'. If it just describes the timing, leave it out.)

Examples for Training:

Text: "treatment of adults with insufficiently controlled type 2 diabetes mellitus as an adjunct to diet and exercise"

Bad Extraction: "insufficiently controlled type 2 diabetes mellitus as an adjunct to diet and exercise"

Good Extraction: "insufficiently controlled type 2 diabetes mellitus"

Text: "treatment of advanced melanoma in adults progressing on platinum-based therapy"

Good Extraction: "advanced melanoma" (Note: "progressing on..." is captured in Treatment Line, not Disease).

Text: "treatment of adults with MSI-H colorectal cancer"

Good Extraction: "MSI-H colorectal cancer"

# Negative Constraints (To prevent Hallucination)
1. DO NOT infer information. If the `Indication_text` does not state the Population, do not guess "Adult".
2. DO NOT include text from the "Disease_level_full_text" into the "Disease + sybtypes" field unless it is explicitly present in the "Indication_text".
3. DO NOT alter the terminology used in the text (e.g., if it says "unresectable", do not change it to "non-operable").

# One-Shot Example (Use this structure exactly)

**Input Text Segment:**
4. 4.1 CLINICAL PARTICULARS Therapeutic indications Melanoma OPDIVO as monotherapy or in combination with ipilimumab is indicated for the treatment of advanced (unresectable or metastatic) melanoma in adults and adolescents 12 years of age and older. Relative to nivolumab monotherapy, an increase in progression-free survival (PFS) and overall survival (OS) for the combination of nivolumab with ipilimumab is established only in patients with low tumour PD-L1 expression (see sections 4.4 and 5.1). Adjuvant treatment of melanoma OPDIVO as monotherapy is indicated for the adjuvant treatment of adults and adolescents 12 years of age and older with Stage IIB or IIC melanoma, or melanoma with involvement of lymph nodes or metastatic disease who have undergone complete resection (see section 5.1). Non-small cell lung cancer (NSCLC) OPDIVO in combination with ipilimumab and 2 cycles of platinum-based chemotherapy is indicated for the first-line treatment of metastatic non-small cell lung cancer in adults whose tumours have no sensitising EGFR mutation or ALK translocation. OPDIVO as monotherapy is indicated for the treatment of locally advanced or metastatic non-small cell lung cancer after prior chemotherapy in adults. 2 Neoadjuvant treatment of NSCLC OPDIVO in combination with platinum-based chemotherapy is indicated for the neoadjuvant treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression â‰¥ 1% (see section 5.1 for selection criteria). Neoadjuvant and adjuvant treatment of NSCLC OPDIVO, in combination with platinum-based chemotherapy as neoadjuvant treatment, followed by OPDIVO as monotherapy as adjuvant treatment, is indicated for the treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression â‰¥ 1% (see section 5.1 for selection criteria). Malignant pleural mesothelioma (MPM) OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable malignant pleural mesothelioma. Renal cell carcinoma (RCC) OPDIVO as monotherapy is indicated for the treatment of advanced renal cell carcinoma after prior therapy in adults. OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with intermediate/poor-risk advanced renal cell carcinoma (see section 5.1). OPDIVO in combination with cabozantinib is indicated for the first-line treatment of adult patients with advanced renal cell carcinoma (see section 5.1). Classical Hodgkin lymphoma (cHL) OPDIVO as monotherapy is indicated for the treatment of adult patients with relapsed or refractory classical Hodgkin lymphoma after autologous stem cell transplant (ASCT) and treatment with brentuximab vedotin. Squamous cell cancer of the head and neck (SCCHN) OPDIVO as monotherapy is indicated for the treatment of recurrent or metastatic squamous cell cancer of the head and neck in adults progressing on or after platinum-based therapy (see section 5.1). Urothelial carcinoma OPDIVO in combination with cisplatin and gemcitabine is indicated for the first-line treatment of adult patients with unresectable or metastatic urothelial carcinoma. OPDIVO as monotherapy is indicated for the treatment of locally advanced unresectable or metastatic urothelial carcinoma in adults after failure of prior platinum-containing therapy. Adjuvant treatment of urothelial carcinoma OPDIVO as monotherapy is indicated for the adjuvant treatment of adults with muscle invasive urothelial carcinoma (MIUC) with tumour cell PD-L1 expression â‰¥ 1%, who are at high risk of recurrence after undergoing radical resection of MIUC (see section 5.1). 3 Mismatch repair deficient (dMMR) or microsatellite instability-high (MSI-H) colorectal cancer (CRC) OPDIVO in combination with ipilimumab is indicated for the treatment of adult patients with mismatch repair deficient or microsatellite instability-high colorectal cancer in the following settings: - - first-line treatment of unresectable or metastatic colorectal cancer; treatment of metastatic colorectal cancer after prior fluoropyrimidine-based combination chemotherapy (see section 5.1). Oesophageal squamous cell carcinoma (OSCC) OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression â‰¥ 1%. OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression â‰¥ 1%. OPDIVO as monotherapy is indicated for the treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma after prior fluoropyrimidine- and platinum-based combination chemotherapy. Adjuvant treatment of oesophageal or gastro-oesophageal junction cancer (OC or GEJC) OPDIVO as monotherapy is indicated for the adjuvant treatment of adult patients with oesophageal or gastro-oesophageal junction cancer who have residual pathologic disease following prior neoadjuvant chemoradiotherapy (see section 5.1). Gastric, gastro-oesophageal junction (GEJ) or oesophageal adenocarcinoma OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with HER2-negative advanced or metastatic gastric, gastro-oesophageal junction or oesophageal adenocarcinoma whose tumours express PD-L1 with a combined positive score (CPS) â‰¥ 5. Hepatocellular carcinoma (HCC) OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable or advanced hepatocellular carcinoma.

output json format:

[
    {
        "Primary Disease_category": "Melanoma",
        "Disease_level_full_text": "Melanoma OPDIVO as monotherapy or in combination with ipilimumab is indicated for the treatment of advanced (unresectable or metastatic) melanoma in adults and adolescents 12 years of age and older. Relative to nivolumab monotherapy, an increase in progression-free survival (PFS) and overall survival (OS) for the combination of nivolumab with ipilimumab is established only in patients with low tumour PD-L1 expression (see sections 4.4 and 5.1). Adjuvant treatment of melanoma OPDIVO as monotherapy is indicated for the adjuvant treatment of adults and adolescents 12 years of age and older with Stage IIB or IIC melanoma, or melanoma with involvement of lymph nodes or metastatic disease who have undergone complete resection (see section 5.1)",
        "Indication #": 1,
        "Indication_text": "OPDIVO as monotherapy or in combination with ipilimumab is indicated for the treatment of advanced (unresectable or metastatic) melanoma in adults and adolescents 12 years of age and older.",
        "Treatment line": "_",
        "Treatment modality": "Monotherapy,Combination",
        "Population": "Adult, Adolescent",
        "Disease + sybtypes": "advanced (unresectable or metastatic)"
    },
    {
        "Primary Disease_category": "Melanoma",
        "Disease_level_full_text": "Melanoma OPDIVO as monotherapy or in combination with ipilimumab is indicated for the treatment of advanced (unresectable or metastatic) melanoma in adults and adolescents 12 years of age and older. Relative to nivolumab monotherapy, an increase in progression-free survival (PFS) and overall survival (OS) for the combination of nivolumab with ipilimumab is established only in patients with low tumour PD-L1 expression (see sections 4.4 and 5.1). Adjuvant treatment of melanoma OPDIVO as monotherapy is indicated for the adjuvant treatment of adults and adolescents 12 years of age and older with Stage IIB or IIC melanoma, or melanoma with involvement of lymph nodes or metastatic disease who have undergone complete resection",
        "Indication #": 2,
        "Indication_text": "OPDIVO as monotherapy is indicated for the adjuvant treatment of adults and adolescents 12 years of age and older with Stage IIB or IIC melanoma, or melanoma with involvement of lymph nodes or metastatic disease who have undergone complete resection.",
        "Treatment line": "_",
        "Treatment modality": "Adjuvant, Monotherapy",
        "Population": "Adult, Adolescent",
        "Disease + sybtypes": "Stage IIB or IIC melanoma, or melanoma with involvement of lymph nodes or metastatic disease"
    },
    {
        "Primary Disease_category": "Non-small cell lung cancer (NSCLC)",
        "Disease_level_full_text": "Non-small cell lung cancer (NSCLC) OPDIVO in combination with ipilimumab and 2 cycles of platinum-based chemotherapy is indicated for the first-line treatment of metastatic non-small cell lung cancer in adults whose tumours have no sensitising EGFR mutation or ALK translocation. OPDIVO as monotherapy is indicated for the treatment of locally advanced or metastatic non-small cell lung cancer after prior chemotherapy in adults. Neoadjuvant treatment of NSCLC OPDIVO in combination with platinum-based chemotherapy is indicated for the neoadjuvant treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria). Neoadjuvant and adjuvant treatment of NSCLC OPDIVO, in combination with platinum-based chemotherapy as neoadjuvant treatment, followed by OPDIVO as monotherapy as adjuvant treatment, is indicated for the treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria).",
        "Indication #": 1,
        "Indication_text": "OPDIVO in combination with ipilimumab and 2 cycles of platinum-based chemotherapy is indicated \nfor the first-line treatment of metastatic non-small cell lung cancer in adults whose tumours have no \nsensitising EGFR mutation or ALK translocation.",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "non-small cell lung cancer in adults whose tumours have no sensitising EGFR mutation or ALK translocation"
    },
    {
        "Primary Disease_category": "Non-small cell lung cancer (NSCLC)",
        "Disease_level_full_text": "Non-small cell lung cancer (NSCLC) OPDIVO in combination with ipilimumab and 2 cycles of platinum-based chemotherapy is indicated for the first-line treatment of metastatic non-small cell lung cancer in adults whose tumours have no sensitising EGFR mutation or ALK translocation. OPDIVO as monotherapy is indicated for the treatment of locally advanced or metastatic non-small cell lung cancer after prior chemotherapy in adults. Neoadjuvant treatment of NSCLC OPDIVO in combination with platinum-based chemotherapy is indicated for the neoadjuvant treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria). Neoadjuvant and adjuvant treatment of NSCLC OPDIVO, in combination with platinum-based chemotherapy as neoadjuvant treatment, followed by OPDIVO as monotherapy as adjuvant treatment, is indicated for the treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria).",
        "Indication #": 2,
        "Indication_text": "OPDIVO as monotherapy is indicated for the treatment of locally advanced or metastatic non-small \ncell lung cancer after prior chemotherapy in adults.",
        "Treatment line": "Second line",
        "Treatment modality": "Monotherapy",
        "Population": "Adult",
        "Disease + sybtypes": "locally advanced or metastatic non-small \ncell lung cancer"
    },
    {
        "Primary Disease_category": "Non-small cell lung cancer (NSCLC)",
        "Disease_level_full_text": "Non-small cell lung cancer (NSCLC) OPDIVO in combination with ipilimumab and 2 cycles of platinum-based chemotherapy is indicated for the first-line treatment of metastatic non-small cell lung cancer in adults whose tumours have no sensitising EGFR mutation or ALK translocation. OPDIVO as monotherapy is indicated for the treatment of locally advanced or metastatic non-small cell lung cancer after prior chemotherapy in adults. Neoadjuvant treatment of NSCLC OPDIVO in combination with platinum-based chemotherapy is indicated for the neoadjuvant treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria). Neoadjuvant and adjuvant treatment of NSCLC OPDIVO, in combination with platinum-based chemotherapy as neoadjuvant treatment, followed by OPDIVO as monotherapy as adjuvant treatment, is indicated for the treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria).",
        "Indication #": 3,
        "Indication_text": "OPDIVO in combination with platinum-based chemotherapy is indicated for the neoadjuvant treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria).",
        "Treatment line": "_",
        "Treatment modality": "Combination, Neoadjuvant",
        "Population": "Adult",
        "Disease + sybtypes": "resectable non-small cell lung cancer at high risk of recurrence"
    },
    {
        "Primary Disease_category": "Non-small cell lung cancer (NSCLC)",
        "Disease_level_full_text": "Non-small cell lung cancer (NSCLC) OPDIVO in combination with ipilimumab and 2 cycles of platinum-based chemotherapy is indicated for the first-line treatment of metastatic non-small cell lung cancer in adults whose tumours have no sensitising EGFR mutation or ALK translocation. OPDIVO as monotherapy is indicated for the treatment of locally advanced or metastatic non-small cell lung cancer after prior chemotherapy in adults. Neoadjuvant treatment of NSCLC OPDIVO in combination with platinum-based chemotherapy is indicated for the neoadjuvant treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria). Neoadjuvant and adjuvant treatment of NSCLC OPDIVO, in combination with platinum-based chemotherapy as neoadjuvant treatment, followed by OPDIVO as monotherapy as adjuvant treatment, is indicated for the treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria).",
        "Indication #": 4,
        "Indication_text": "OPDIVO, in combination with platinum-based chemotherapy as neoadjuvant treatment, followed by OPDIVO as monotherapy as adjuvant treatment, is indicated for the treatment of resectable non-small cell lung cancer at high risk of recurrence in adult patients whose tumours have PD-L1 expression \u2265 1% (see section 5.1 for selection criteria).",
        "Treatment line": "_",
        "Treatment modality": "Combination, Neoadjuvant, Adjuvant, Monotherapy",
        "Population": "Adult",
        "Disease + sybtypes": "resectable non-small \ncell lung cancer at high risk of recurrence"
    },
    {
        "Primary Disease_category": "Malignant pleural mesothelioma (MPM)",
        "Disease_level_full_text": "Malignant pleural mesothelioma (MPM) OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable malignant pleural mesothelioma.",
        "Indication #": 1,
        "Indication_text": "OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable malignant pleural mesothelioma.",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "unresectable malignant pleural mesothelioma"
    },
    {
        "Primary Disease_category": "Renal cell carcinoma (RCC)",
        "Disease_level_full_text": "Renal cell carcinoma (RCC) OPDIVO as monotherapy is indicated for the treatment of advanced renal cell carcinoma after prior therapy in adults. OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with intermediate/poor-risk advanced renal cell carcinoma (see section 5.1). OPDIVO in combination with cabozantinib is indicated for the first-line treatment of adult patients with advanced renal cell carcinoma (see section 5.1).",
        "Indication #": 1,
        "Indication_text": "OPDIVO as monotherapy is indicated for the treatment of advanced renal cell carcinoma after prior therapy in adults",
        "Treatment line": "Second line",
        "Treatment modality": "Monotherapy",
        "Population": "Adult",
        "Disease + sybtypes": "advanced renal cell carcinoma"
    },
    {
        "Primary Disease_category": "Renal cell carcinoma (RCC)",
        "Disease_level_full_text": "Renal cell carcinoma (RCC) OPDIVO as monotherapy is indicated for the treatment of advanced renal cell carcinoma after prior therapy in adults. OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with intermediate/poor-risk advanced renal cell carcinoma (see section 5.1). OPDIVO in combination with cabozantinib is indicated for the first-line treatment of adult patients with advanced renal cell carcinoma (see section 5.1).",
        "Indication #": 2,
        "Indication_text": "OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with intermediate/poor-risk advanced renal cell carcinoma",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "intermediate/poor-risk advanced renal cell carcinoma"
    },
    {
        "Primary Disease_category": "Renal cell carcinoma (RCC)",
        "Disease_level_full_text": "Renal cell carcinoma (RCC) OPDIVO as monotherapy is indicated for the treatment of advanced renal cell carcinoma after prior therapy in adults. OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with intermediate/poor-risk advanced renal cell carcinoma (see section 5.1). OPDIVO in combination with cabozantinib is indicated for the first-line treatment of adult patients with advanced renal cell carcinoma (see section 5.1).",
        "Indication #": 3,
        "Indication_text": "OPDIVO in combination with cabozantinib is indicated for the first-line treatment of adult patients with advanced renal cell carcinoma",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "advanced renal cell carcinoma"
    },
    {
        "Primary Disease_category": "Classical Hodgkin lymphoma (cHL)",
        "Disease_level_full_text": "Classical Hodgkin lymphoma (cHL) OPDIVO as monotherapy is indicated for the treatment of adult patients with relapsed or refractory classical Hodgkin lymphoma after autologous stem cell transplant (ASCT) and treatment with brentuximab vedotin.",
        "Indication #": 1,
        "Indication_text": "OPDIVO as monotherapy is indicated for the treatment of adult patients with relapsed or refractory classical Hodgkin lymphoma after autologous stem cell transplant (ASCT) and treatment with brentuximab vedotin",
        "Treatment line": "Third line",
        "Treatment modality": "Monotherapy",
        "Population": "Adult",
        "Disease + sybtypes": "relapsed or refractory classical Hodgkin lymphoma"
    },
    {
        "Primary Disease_category": "Squamous cell cancer of the head and neck (SCCHN)",
        "Disease_level_full_text": "Squamous cell cancer of the head and neck (SCCHN) OPDIVO as monotherapy is indicated for the treatment of recurrent or metastatic squamous cell cancer of the head and neck in adults progressing on or after platinum-based therapy",
        "Indication #": 1,
        "Indication_text": "OPDIVO as monotherapy is indicated for the treatment of recurrent or metastatic squamous cell cancer of the head and neck in adults progressing on or after platinum-based therapy",
        "Treatment line": "Second line",
        "Treatment modality": "Monotherapy",
        "Population": "Adult",
        "Disease + sybtypes": "recurrent or metastatic squamous cell cancer of the head and neck"
    },
    {
        "Primary Disease_category": "Urothelial carcinoma",
        "Disease_level_full_text": "Urothelial carcinoma OPDIVO in combination with cisplatin and gemcitabine is indicated for the first-line treatment of adult patients with unresectable or metastatic urothelial carcinoma. OPDIVO as monotherapy is indicated for the treatment of locally advanced unresectable or metastatic urothelial carcinoma in adults after failure of prior platinum-containing therapy. Adjuvant treatment of urothelial carcinoma OPDIVO as monotherapy is indicated for the adjuvant treatment of adults with muscle invasive urothelial carcinoma (MIUC) with tumour cell PD-L1 expression \u2265 1%, who are at high risk of recurrence after undergoing radical resection of MIUC (see section 5.1).",
        "Indication #": 1,
        "Indication_text": "OPDIVO in combination with cisplatin and gemcitabine is indicated for the first-line treatment of adult patients with unresectable or metastatic urothelial carcinoma.",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "unresectable or metastatic urothelial carcinoma"
    },
    {
        "Primary Disease_category": "Urothelial carcinoma",
        "Disease_level_full_text": "Urothelial carcinoma OPDIVO in combination with cisplatin and gemcitabine is indicated for the first-line treatment of adult patients with unresectable or metastatic urothelial carcinoma. OPDIVO as monotherapy is indicated for the treatment of locally advanced unresectable or metastatic urothelial carcinoma in adults after failure of prior platinum-containing therapy. Adjuvant treatment of urothelial carcinoma OPDIVO as monotherapy is indicated for the adjuvant treatment of adults with muscle invasive urothelial carcinoma (MIUC) with tumour cell PD-L1 expression \u2265 1%, who are at high risk of recurrence after undergoing radical resection of MIUC (see section 5.1).",
        "Indication #": 2,
        "Indication_text": "OPDIVO as monotherapy is indicated for the treatment of locally advanced unresectable or metastatic urothelial carcinoma in adults after failure of prior platinum-containing therapy",
        "Treatment line": "Second line",
        "Treatment modality": "Monotherapy",
        "Population": "Adult",
        "Disease + sybtypes": "locally advanced unresectable or metastatic urothelial carcinoma"
    },
    {
        "Primary Disease_category": "Urothelial carcinoma",
        "Disease_level_full_text": "Urothelial carcinoma OPDIVO in combination with cisplatin and gemcitabine is indicated for the first-line treatment of adult patients with unresectable or metastatic urothelial carcinoma. OPDIVO as monotherapy is indicated for the treatment of locally advanced unresectable or metastatic urothelial carcinoma in adults after failure of prior platinum-containing therapy. Adjuvant treatment of urothelial carcinoma OPDIVO as monotherapy is indicated for the adjuvant treatment of adults with muscle invasive urothelial carcinoma (MIUC) with tumour cell PD-L1 expression \u2265 1%, who are at high risk of recurrence after undergoing radical resection of MIUC (see section 5.1)",
        "Indication #": 3,
        "Indication_text": "OPDIVO as monotherapy is indicated for the adjuvant treatment of adults with muscle invasive urothelial carcinoma (MIUC) with tumour cell PD-L1 expression \u2265 1%, who are at high risk of recurrence after undergoing radical resection of MIUC",
        "Treatment line": "Second line",
        "Treatment modality": "Monotherapy,Adjuvant",
        "Population": "Adult",
        "Disease + sybtypes": "muscle invasive urothelial carcinoma (MIUC) with tumour cell PD-L1 expression \u2265 1%, who are at high risk of recurrence"
    },
    {
        "Primary Disease_category": "Mismatch repair deficient (dMMR) or microsatellite instability-high (MSI-H) colorectal cancer (CRC)",
        "Disease_level_full_text": "Mismatch repair deficient (dMMR) or microsatellite instability-high (MSI-H) colorectal cancer (CRC) OPDIVO in combination with ipilimumab is indicated for the treatment of adult patients with mismatch repair deficient or microsatellite instability-high colorectal cancer in the following settings: - - first-line treatment of unresectable or metastatic colorectal cancer; treatment of metastatic colorectal cancer after prior fluoropyrimidine-based combination chemotherapy",
        "Indication #": 1,
        "Indication_text": "OPDIVO in combination with ipilimumab is indicated for the treatment of adult patients with mismatch repair deficient or microsatellite instability-high colorectal cancer in the following settings: - - first-line treatment of unresectable or metastatic colorectal cancer",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "unresectable or metastatic colorectal cancer"
    },
    {
        "Primary Disease_category": "Mismatch repair deficient (dMMR) or microsatellite instability-high (MSI-H) colorectal cancer (CRC)",
        "Disease_level_full_text": "Mismatch repair deficient (dMMR) or microsatellite instability-high (MSI-H) colorectal cancer (CRC) OPDIVO in combination with ipilimumab is indicated for the treatment of adult patients with mismatch repair deficient or microsatellite instability-high colorectal cancer in the following settings: - - first-line treatment of unresectable or metastatic colorectal cancer; treatment of metastatic colorectal cancer after prior fluoropyrimidine-based combination chemotherapy",
        "Indication #": 2,
        "Indication_text": "OPDIVO in combination with ipilimumab is indicated for the treatment of adult patients with mismatch repair deficient or microsatellite instability-high colorectal cancer in the following settings-treatment of metastatic colorectal cancer after prior fluoropyrimidine-based combination chemotherapy",
        "Treatment line": "Second line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "metastatic colorectal cancer"
    },
    {
        "Primary Disease_category": "Oesophageal squamous cell carcinoma (OSCC)",
        "Disease_level_full_text": "Oesophageal squamous cell carcinoma (OSCC) OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%. OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%. OPDIVO as monotherapy is indicated for the treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma after prior fluoropyrimidine- and platinum-based combination chemotherapy.",
        "Indication #": 1,
        "Indication_text": "OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma"
    },
    {
        "Primary Disease_category": "Oesophageal squamous cell carcinoma (OSCC)",
        "Disease_level_full_text": "Oesophageal squamous cell carcinoma (OSCC) OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%. OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%. OPDIVO as monotherapy is indicated for the treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma after prior fluoropyrimidine- and platinum-based combination chemotherapy.",
        "Indication #": 2,
        "Indication_text": "OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma"
    },
    {
        "Primary Disease_category": "Oesophageal squamous cell carcinoma (OSCC)",
        "Disease_level_full_text": "Oesophageal squamous cell carcinoma (OSCC) OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%. OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma with tumour cell PD-L1 expression \u2265 1%. OPDIVO as monotherapy is indicated for the treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma after prior fluoropyrimidine- and platinum-based combination chemotherapy.",
        "Indication #": 3,
        "Indication_text": "OPDIVO as monotherapy is indicated for the treatment of adult patients with unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma after prior fluoropyrimidine- and platinum-based combination chemotherapy",
        "Treatment line": "Second line",
        "Treatment modality": "Monotherapy",
        "Population": "Adult",
        "Disease + sybtypes": "unresectable advanced, recurrent or metastatic oesophageal squamous cell carcinoma"
    },
    {
        "Primary Disease_category": "Oesophageal or gastro-oesophageal junction cancer (OC or GEJC)",
        "Disease_level_full_text": "Adjuvant treatment of oesophageal or gastro-oesophageal junction cancer (OC or GEJC) OPDIVO as monotherapy is indicated for the adjuvant treatment of adult patients with oesophageal or gastro-oesophageal junction cancer who have residual pathologic disease following prior neoadjuvant chemoradiotherapy",
        "Indication #": 1,
        "Indication_text": "OPDIVO as monotherapy is indicated for the adjuvant treatment of adult patients with oesophageal or gastro-oesophageal junction cancer who have residual pathologic disease following prior neoadjuvant chemoradiotherapy",
        "Treatment line": "Second line",
        "Treatment modality": "Monotherapy,Adjuvant",
        "Population": "Adult",
        "Disease + sybtypes": "oesophageal or gastro-oesophageal junction cancer who have residual pathologic disease"
    },
    {
        "Primary Disease_category": "Gastric, gastro-oesophageal junction (GEJ) or oesophageal adenocarcinoma",
        "Disease_level_full_text": "Gastric, gastro-oesophageal junction (GEJ) or oesophageal adenocarcinoma OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with HER2-negative advanced or metastatic gastric, gastro-oesophageal junction or oesophageal adenocarcinoma whose tumours express PD-L1 with a combined positive score (CPS) \u2265 5",
        "Indication #": 1,
        "Indication_text": "OPDIVO in combination with fluoropyrimidine- and platinum-based combination chemotherapy is indicated for the first-line treatment of adult patients with HER2-negative advanced or metastatic gastric, gastro-oesophageal junction or oesophageal adenocarcinoma whose tumours express PD-L1 with a combined positive score (CPS) \u2265 5",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "HER2-negative advanced or metastatic gastric, gastro-oesophageal junction or oesophageal adenocarcinoma"
    },
    {
        "Primary Disease_category": "Hepatocellular carcinoma (HCC)",
        "Disease_level_full_text": "OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable or advanced hepatocellular carcinoma",
        "Indication #": 1,
        "Indication_text": "OPDIVO in combination with ipilimumab is indicated for the first-line treatment of adult patients with unresectable or advanced hepatocellular carcinoma",
        "Treatment line": "First line",
        "Treatment modality": "Combination",
        "Population": "Adult",
        "Disease + sybtypes": "unresectable or advanced hepatocellular carcinoma"
    },
    {
        "Primary Disease_category": "Neovascular (wet) age-related macular degeneration (AMD)",
        "Disease_level_full_text": "Lucentis is indicated in adults for: The treatment of neovascular (wet) age-related macular degeneration (AMD)",
        "Indication #": 1,
        "Indication_text": "Lucentis is indicated in adults for: The treatment of neovascular (wet) age-related macular degeneration (AMD)",
        "Treatment line": "_",
        "Treatment modality": "_",
        "Population": "Adult",
        "Disease + sybtypes": "neovascular (wet) age-related macular degeneration (AMD)"
    }
]
"""


# Function to clean JSON response
# Function to clean JSON response
def clean_json_response(response_text):
    """
    Clean the response text by removing ```
    """
    cleaned = response_text.strip()
    
    # Define markers using string concatenation to avoid syntax issues
    json_marker = "`" + "`" + "`" + "json"
    code_marker = "`" + "`" + "`"
    
    # Remove ```json or ```
    if cleaned.startswith(json_marker):
        cleaned = cleaned[len(json_marker):]
    elif cleaned.startswith(code_marker):
        cleaned = cleaned[len(code_marker):]
    
    # Remove ``` at the end
    if cleaned.endswith(code_marker):
        cleaned = cleaned[:-len(code_marker)]
    
    return cleaned.strip()


# Function to display JSON beautifully
def display_json_beautifully(json_data):
    """Display JSON data in a beautiful format"""
    
    if isinstance(json_data, dict):
        # Check if it's a list of indications or similar structure
        if "indications" in json_data:
            st.markdown("### 📋 Extracted Indications")
            for idx, indication in enumerate(json_data["indications"], 1):
                with st.expander(f"**{idx}. {indication.get('indication_name', 'Indication')}**", expanded=True):
                    for key, value in indication.items():
                        if key != "indication_name":
                            if isinstance(value, list):
                                st.markdown(f"**{key.replace('_', ' ').title()}:**")
                                for item in value:
                                    st.markdown(f"  - {item}")
                            else:
                                st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
        else:
            # Generic JSON display
            for key, value in json_data.items():
                if isinstance(value, list):
                    st.markdown(f"### {key.replace('_', ' ').title()}")
                    for idx, item in enumerate(value, 1):
                        if isinstance(item, dict):
                            with st.expander(f"**Item {idx}**", expanded=True):
                                for k, v in item.items():
                                    if isinstance(v, list):
                                        st.markdown(f"**{k.replace('_', ' ').title()}:**")
                                        for i in v:
                                            st.markdown(f"  - {i}")
                                    else:
                                        st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                        else:
                            st.markdown(f"- {item}")
                elif isinstance(value, dict):
                    st.markdown(f"### {key.replace('_', ' ').title()}")
                    for k, v in value.items():
                        st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                else:
                    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
    
    elif isinstance(json_data, list):
        st.markdown("### 📋 Extracted Information")
        for idx, item in enumerate(json_data, 1):
            if isinstance(item, dict):
                # Try to find a name/title field for the expander
                title = item.get('indication_name') or item.get('name') or item.get('title') or f"Item {idx}"
                with st.expander(f"**{idx}. {title}**", expanded=True):
                    for key, value in item.items():
                        if key not in ['indication_name', 'name', 'title']:
                            if isinstance(value, list):
                                st.markdown(f"**{key.replace('_', ' ').title()}:**")
                                for v in value:
                                    st.markdown(f"  - {v}")
                            else:
                                st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
            else:
                st.markdown(f"- {item}")

# API Key Input
st.markdown("### 🔑 API Configuration")
api_key = st.text_input(
    "Enter your Gemini API Key",
    type="password",
    placeholder="Enter your Gemini API key here...",
    help="Your API key will be used to make calls to the Gemini API"
)

st.markdown("---")

# Text Input Area
st.markdown("### 📝 Input Text")
input_text = st.text_area(
    "Paste your plain text here",
    height=200,
    placeholder="Paste the EMA document text here for extraction...",
    help="Paste the clinical/medical text that you want to extract information from"
)

st.markdown("")

# Extract Button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    extract_button = st.button("🔍 Extract Info", use_container_width=True)

st.markdown("---")

# Process when button is clicked
if extract_button:
    if not api_key:
        st.error("⚠️ Please enter your Gemini API Key!")
    elif not input_text:
        st.error("⚠️ Please paste some text to extract information from!")
    else:
        try:
            with st.spinner("🔄 Extracting information... Please wait..."):
                # Import and initialize Gemini client
                from google import genai
                
                client = genai.Client(api_key=api_key)
                
                # Make API call
                response = client.models.generate_content(
                    model="gemini-2.5-flash-preview-09-2025",
                    contents=[input_text, cdp_ema_prompt]
                )
                
                # Get response text
                response_text = response.text
                
                # Clean the JSON response (remove ```json and ```
                cleaned_response = clean_json_response(response_text)
                
                # Parse JSON
                try:
                    json_data = json.loads(cleaned_response)
                    
                    st.success("✅ Information extracted successfully!")
                    
                    # Display results in tabs
                    tab1, tab2 = st.tabs(["📊 Formatted View", "🔤 Raw JSON"])
                    
                    with tab1:
                        display_json_beautifully(json_data)
                    
                    with tab2:
                        st.json(json_data)
                        
                        # Download button for JSON
                        st.download_button(
                            label="📥 Download JSON",
                            data=json.dumps(json_data, indent=2),
                            file_name="extracted_data.json",
                            mime="application/json"
                        )
                
                except json.JSONDecodeError as e:
                    st.warning("⚠️ Response is not in JSON format. Displaying raw response:")
                    st.text_area("Raw Response", response_text, height=300)
                    
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Please check your API key and try again.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    <p>EMA Extraction Tool | Powered by Gemini AI</p>
</div>
""", unsafe_allow_html=True)
