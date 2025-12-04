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
cdp_ema_prompt = """prompt here"""  # Replace with your actual prompt

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
                    model="gemini-2.5-flash-preview-05-20",
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
