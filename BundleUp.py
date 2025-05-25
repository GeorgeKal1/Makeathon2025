import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import os

# --- Google API Setup ---
API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY')  
genai.configure(api_key=API_KEY) 
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Load Data ---
@st.cache_data
def load_data(file_path, sheet):
    try:
        return pd.read_excel(file_path, sheet_name=sheet).head(1600)
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return pd.DataFrame().head(1600)    

# --- Generate AI Bundles ---
def generate_bundles(focus_product, related_products, based_on="product"):
    if based_on == "product":
        all_products = [focus_product] + related_products
        focus_title = focus_product.get("Item title", "N/A")

        product_list_str = "\n".join([
            f"- {p.get('Item title', 'N/A')} "
            f"(Κατηγορία: {p.get('Category', 'N/A')}, "
            f"Τιμή: €{p.get('FinalLineTotal', 0.0):.2f}, "
            f"Απόθεμα: {p.get('Quantity', 'N/A')})"
            for p in all_products
        ])

        prompt = f"""
Είσαι ειδικός στο ηλεκτρονικό εμπόριο. Δημιούργησε 3–5 δημιουργικά πακέτα προϊόντων με βάση τον εξής κατάλογο.

Απαραίτητα:
- Κάθε πακέτο ΠΡΕΠΕΙ να περιλαμβάνει το βασικό προϊόν:
  "{focus_title}"
- Να συνδυάζεις με 1–3 σχετικά προϊόντα από τη λίστα.
- Πρόσθεσε ευφάνταστο όνομα και δίκαιη προτεινόμενη τιμή με έκπτωση 10-25%.
- Συνδύασε φτηνά με ακριβά προϊόντα, λιγότερο αγορασμένα με δημοφιλή.
- Συνολικό κόστος πακέτου: €50 – €200.

Λίστα προϊόντων:
{product_list_str}

**IMPORTANT**: Return ONLY valid JSON. Do not include any markdown, comments, or text before/after.
[
  {{
    "bundleName": "string",
    "productsInBundle": ["string", ...],
    "suggestedPrice": number
  }},
  ...
]
"""
    
    elif based_on == "category":
        product_list_str = "\n".join([
            f"- {p.get('Item title', 'N/A')} "
            f"(Κατηγορία: {p.get('Category', 'N/A')}, "
            f"Τιμή: €{p.get('FinalLineTotal', 0.0):.2f}, "
            f"Απόθεμα: {p.get('Quantity', 'N/A')})"
            for p in related_products
        ])

        prompt = f"""
Είσαι ειδικός στο ηλεκτρονικό εμπόριο. Δημιούργησε 3–5 πακέτα προϊόντων από την ίδια κατηγορία.

Απαραίτητα:
- Κάθε πακέτο να περιλαμβάνει 2–4 προϊόντα που ταιριάζουν καλά μαζί.
- Φτιάξε ευφάνταστο όνομα για κάθε πακέτο και πρόσθεσε ελκυστική τιμή με έκπτωση 10-25%.
- Τα πακέτα πρέπει να έχουν συνολική αξία (πριν την έκπτωση) μεταξύ €50 και €200.
- Βρες συνδυασμούς που έχουν νόημα και θα άρεσαν στον πελάτη.

Λίστα προϊόντων:
{product_list_str}

**IMPORTANT**: Return ONLY valid JSON. Do not include any markdown, comments, or text before/after.
[
  {{
    "bundleName": "string",
    "productsInBundle": ["string", ...],
    "suggestedPrice": number
  }},
  ...
]
"""

    else:
        st.error("❌ Μη υποστηριζόμενη μέθοδος αναζήτησης.")
        return []

    # --- Gemini API Call ---
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("```").strip("json").strip()

        first_bracket = raw_text.find("[")
        last_bracket = raw_text.rfind("]") + 1
        json_text = raw_text[first_bracket:last_bracket]

        bundles = json.loads(json_text)
        return bundles

    except Exception as e:
        st.error(f"❌ Σφάλμα Gemini ή JSON: {e}")
        return []



# --- Streamlit UI ---
st.set_page_config(page_title="BundleUp", layout="centered")
st.title("📦 BundleUp")
st.text("Every purchase is a chance to bundle up! Ας κάνουμε κάποιες φοβερές αγορές μαζί! \n 😏7% από τα κέρδη πάνε στους Γιατρούς χωρίς σύνορα!!! \n\n")

# Load your Excel file
excel_path = "customerdata.xlsx"  # Make sure this file is in the same folder
sheet_name = "orders"
df = load_data(excel_path, sheet_name)

if df.empty:
    st.stop()

# Product search
# Επιλογή τρόπου αναζήτησης

search_mode = st.radio("🔎 Πώς θέλεις να ψάξεις;", ["Όνομα προϊόντος", "Κατηγορία"])

user_query = st.text_input("🔍 Πληκτρολόγησε το προϊόν ή την κατηγορία που σε ενδιαφέρει:")

if user_query:
    if search_mode == "Όνομα προϊόντος":
        matches = df[df['Item title'].str.contains(user_query, case=False, na=False)]
        if matches.empty:
            st.warning("❌ Δεν βρέθηκαν σχετικά προϊόντα.")
        else:
            focus_product = matches.iloc[0].to_dict()
            st.success(f"✅ Χρησιμοποιείται: {focus_product['Item title']}")

            brand = str(focus_product.get('Brand', '')).lower()
            category = str(focus_product.get('Category', '')).lower()
            price = float(focus_product.get('FinalLineTotal', 0.0))

            related_df = df[
                (df['Item title'] != focus_product['Item title']) & (
                    (df['Brand'].astype(str).str.lower() == brand) |
                    (df['Category'].astype(str).str.lower() == category) |
                    (df['FinalLineTotal'].between(price - 20, price + 20))
                )
            ]

            related_products = related_df.to_dict(orient='records')
            based_on = "product"

    else:  # Κατηγορία
        category_df = df[df['Category'].str.contains(user_query, case=False, na=False)]
        if category_df.empty:
            st.warning("❌ Δεν βρέθηκαν προϊόντα σε αυτή την κατηγορία.")
        else:
            st.success(f"✅ Βρέθηκαν {len(category_df)} προϊόντα στην κατηγορία: {user_query}")
            focus_product = None
            related_products = category_df.to_dict(orient='records')
            based_on = "category"

    if st.button("✨ Δημιούργησε AI Bundles"):
        with st.spinner("🧠 Σκέφτομαι..."):
            bundles = generate_bundles(focus_product, related_products, based_on=based_on)

        if bundles:
            for bundle in bundles:
                included_titles = bundle["productsInBundle"]
                actual_products = df[df['Item title'].isin(included_titles)]
                full_price = actual_products['FinalLineTotal'].sum()
                suggested_price = bundle['suggestedPrice']

                if full_price - suggested_price > 0 and (full_price - suggested_price)/full_price < 0.28:
                    discount_percentage = 100 * (full_price - suggested_price) / full_price
                    discount_message = f"🎉 Κερδίζεις {discount_percentage:.0f}%! Καλή Επιλογή🔥!"

                    st.markdown(f"### 📦 {bundle['bundleName']}")
                    st.markdown("**Τι περιλαμβάνεται:**")
                    st.markdown("\n".join([f"- {p}" for p in included_titles]))
                    st.markdown(f"💰 **Προτεινόμενη Τιμή:** €{suggested_price:.2f}")
                    st.markdown(f"🧮 **Αρχική Τιμή:** €{full_price:.2f}")
                    st.markdown(f"💡 {discount_message}")
                    st.markdown("---")
        else:
            st.warning("⚠️ Δεν επιστράφηκαν προτάσεις bundles.")


