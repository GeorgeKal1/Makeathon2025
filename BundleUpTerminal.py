import pandas as pd
import google.generativeai as genai
import json
import os

# --- Google API Setup ---
API_KEY = os.getenv('GEMINI_API_KEY', 'Your-API-Key-Here')  # Replace with your actual API key
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Load Data ---
def load_data(file_path, sheet):
    try:
        return pd.read_excel(file_path, sheet_name=sheet).head(600)
    except Exception as e:
        print(f"❌ Σφάλμα ανάγνωσης Excel: {e}")
        return pd.DataFrame()

# --- AI Bundle Generator ---
def generate_bundles(focus_product, related_products, based_on="product"):
    if based_on == "product":
        all_products = [focus_product] + related_products
        focus_title = focus_product.get("Item title", "N/A")
        product_list_str = "\n".join([
            f"- {p.get('Item title', 'N/A')} (Κατηγορία: {p.get('Category', 'N/A')}, Τιμή: €{p.get('FinalLineTotal', 0.0):.2f}, Απόθεμα: {p.get('Quantity', 'N/A')})"
            for p in all_products
        ])
        prompt = f"""
Είσαι ειδικός στο ηλεκτρονικό εμπόριο. Δημιούργησε 3–5 δημιουργικά πακέτα προϊόντων με βάση τον εξής κατάλογο.

Απαραίτητα:
- Κάθε πακέτο ΠΡΕΠΕΙ να περιλαμβάνει το βασικό προϊόν: "{focus_title}"
- Να συνδυάζεις με 1–3 σχετικά προϊόντα από τη λίστα.
- Πρόσθεσε ευφάνταστο όνομα και δίκαιη προτεινόμενη τιμή με έκπτωση 10-25%.
- Συνολικό κόστος πακέτου: €50 – €200.

Λίστα προϊόντων:
{product_list_str}

**IMPORTANT**: Return ONLY valid JSON. Do not include markdown or text before/after.
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
            f"- {p.get('Item title', 'N/A')} (Κατηγορία: {p.get('Category', 'N/A')}, Τιμή: €{p.get('FinalLineTotal', 0.0):.2f}, Απόθεμα: {p.get('Quantity', 'N/A')})"
            for p in related_products
        ])
        prompt = f"""
Είσαι ειδικός στο ηλεκτρονικό εμπόριο. Δημιούργησε 3–5 πακέτα προϊόντων από την ίδια κατηγορία.

Απαραίτητα:
- Κάθε πακέτο να περιλαμβάνει 2–4 προϊόντα που ταιριάζουν καλά μαζί.
- Φτιάξε ευφάνταστο όνομα και πρόσθεσε ελκυστική τιμή με έκπτωση 10-25%.
- Συνολική αξία πακέτου: €50 – €200.

Λίστα προϊόντων:
{product_list_str}

**IMPORTANT**: Return ONLY valid JSON. Do not include markdown or text before/after.
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
        print("❌ Άκυρη μέθοδος αναζήτησης.")
        return []

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("```").strip("json").strip()
        json_text = raw_text[raw_text.find("["):raw_text.rfind("]")+1]
        return json.loads(json_text)
    except Exception as e:
        print(f"❌ Σφάλμα AI ή JSON: {e}")
        return []

# --- Main CLI App ---
def main():
    print("\n📦 Καλωσήρθες στο BundleUp (CLI Edition)!")
    print("10% των κερδών πάνε στους Γιατρούς χωρίς Σύνορα!\n")

    df = load_data("customerdata.xlsx", "orders")
    if df.empty:
        print("❌ Δεν υπάρχουν δεδομένα.")
        return

    print("Πώς θέλεις να ψάξεις;\n1. Όνομα προϊόντος\n2. Κατηγορία")
    choice = input("Επίλεξε (1 ή 2): ").strip()

    if choice == "1":
        query = input("🔍 Πληκτρολόγησε το όνομα προϊόντος: ").strip()
        matches = df[df['Item title'].str.contains(query, case=False, na=False)]
        if matches.empty:
            print("❌ Δεν βρέθηκαν προϊόντα.")
            return
        focus_product = matches.iloc[0].to_dict()
        print(f"✅ Επέλεξες: {focus_product['Item title']}")

        related_df = df[
            (df['Item title'] != focus_product['Item title']) &
            (
                (df['Brand'].astype(str).str.lower() == str(focus_product.get('Brand', '')).lower()) |
                (df['Category'].astype(str).str.lower() == str(focus_product.get('Category', '')).lower()) |
                (df['FinalLineTotal'].between(float(focus_product.get('FinalLineTotal', 0)) - 20,
                                              float(focus_product.get('FinalLineTotal', 0)) + 20))
            )
        ]
        related_products = related_df.to_dict(orient='records')
        based_on = "product"

    elif choice == "2":
        query = input("🔍 Πληκτρολόγησε την κατηγορία: ").strip()
        matches = df[df['Category'].str.contains(query, case=False, na=False)]
        if matches.empty:
            print("❌ Δεν βρέθηκαν προϊόντα στην κατηγορία.")
            return
        print(f"✅ Βρέθηκαν {len(matches)} προϊόντα.")
        focus_product = None
        related_products = matches.to_dict(orient='records')
        based_on = "category"
    else:
        print("❌ Άκυρη επιλογή.")
        return

    input("🧠 Πάτα Enter για να δημιουργήσεις AI Bundles...")

    bundles = generate_bundles(focus_product, related_products, based_on)

    if not bundles:
        print("⚠️ Δεν επιστράφηκαν προτάσεις.")
        return

    for bundle in bundles:
        titles = bundle["productsInBundle"]
        actual = df[df['Item title'].isin(titles)]
        full_price = actual['FinalLineTotal'].sum()
        suggested = bundle['suggestedPrice']
        discount = 100 * (full_price - suggested) / full_price if full_price else 0

        print(f"\n📦 {bundle['bundleName']}")
        print("🛒 Προϊόντα:")
        for t in titles:
            print(f"- {t}")
        print(f"💰 Τιμή Πακέτου: €{suggested:.2f}")
        print(f"🧾 Κανονική Τιμή: €{full_price:.2f}")
        print(f"🎉 Έκπτωση: {discount:.0f}%")
        print("-" * 40)

if __name__ == "__main__":
    main()
