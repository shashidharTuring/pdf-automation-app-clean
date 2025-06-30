
import os
import fitz
from PIL import Image
from io import BytesIO
import base64
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyzer.gpt_utils import gpt4o_image_prompt, call_gpt4o
from analyzer.image_utils import is_chart_like
from analyzer.drive_uploader import upload_file_to_drive  # ✅ import uploader

def load_prompt(path):
    with open(path, 'r') as f:
        return f.read()
# Redefine the missing extract_flag function
import re
import pandas as pd

def extract_flag(text, key):
    pattern = rf"\*\*{re.escape(key)}:\*\*\s*(Yes|No)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip().lower() == "yes" if match else None
# def extract_gpt_flags(description):
#     def extract_flag(label):
#         pattern = rf"-\s+\*\*{label}\*\*\s*[:：]?\s*(yes|no)"
#         match = re.search(pattern, description, re.IGNORECASE)
#         return match.group(1).strip().lower() if match else "no"

#     return {
#         "infographics_gpt": extract_flag("Infographics"),
#         "charts_gpt": extract_flag("Charts"),
#         "financial_tables_gpt": extract_flag("Financial Tables"),
#     }




def analyze_pdf(pdf_path, progress_callback=None, max_workers=8):
    doc = fitz.open(pdf_path)
    figure_pattern = re.compile(r"(figure|fig)\.? ?\d+", re.I)
    table_pattern = re.compile(r"(table|tbl)\.? ?\d+", re.I)
    results = []
    base64_images_all_pages = []

    def process_single_page(page, page_no):
        has_infographic = bool(page.get_images(full=True))
        has_chart = False
        has_table = False

        blocks = page.get_text("dict")["blocks"]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        page_image = Image.open(BytesIO(pix.tobytes("png")))
        page_width, page_height = page_image.size

        for block in blocks:
            if block["type"] != 0:
                continue
            text = " ".join([span["text"] for line in block["lines"] for span in line["spans"]]).lower()
            if figure_pattern.search(text):
                y0 = int(block['bbox'][1] * 1.5)
                crop_top = max(0, int((block['bbox'][1] - 100) * 1.5))
                cropped = page_image.crop((0, crop_top, page_width, y0))
                if is_chart_like(cropped):
                    has_chart = True
            if table_pattern.search(text) or "₹" in text or "$" in text or "%" in text:
                has_table = True

        if has_infographic or has_chart or has_table:
            buffered = BytesIO()
            page_image.save(buffered, format="PNG")
            base64_img = base64.b64encode(buffered.getvalue()).decode()
            base64_images_all_pages.append(base64_img)

            prompt_text = load_prompt("prompts/page_analysis_prompt.txt").format(
                page_no=page_no,
                infographics="yes" if has_infographic else "no",
                charts="yes" if has_chart else "no",
                tables="yes" if has_table else "no"
            )
            gpt_response = call_gpt4o(prompt_text, [base64_img])
        else:
            gpt_response = "Page skipped."

        return {
            "page_no": page_no + 1,
            "infographics": "yes" if has_infographic else "no",
            "charts": "yes" if has_chart else "no",
            "financial_tables": "yes" if has_table else "no",
            "gpt4o_description": gpt_response
        }

    # Parallel processing
    total_pages = len(doc)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_single_page, page, i) for i, page in enumerate(doc)]
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            results.append(result)
            if progress_callback:
                progress_callback(i + 1, total_pages)

    # Summarize the whole PDF
    summary_prompt = load_prompt("prompts/pdf_summary_prompt.txt")
    pdf_summary = call_gpt4o(summary_prompt, base64_images_all_pages[:10])
    print(f"\n📘 Summary:\n{pdf_summary}")

    # Final output
    df = pd.DataFrame(results)


    

    infographics_gpt = []
    charts_gpt = []
    financial_tables_gpt = []

    for idx, row in df.iterrows():
        gpt_text = row.get("gpt4o_description", "")
        infographics_gpt.append(extract_flag(gpt_text, "Infographics"))
        charts_gpt.append(extract_flag(gpt_text, "Charts"))
        financial_tables_gpt.append(extract_flag(gpt_text, "Financial Tables"))

    
    # Add extracted columns
    df["infographics_gpt"] = infographics_gpt
    df["charts_gpt"] = charts_gpt
    df["financial_tables_gpt"] = financial_tables_gpt


    


    # Convert True/False to 'yes'/'no'
    for col in ["infographics_gpt", "charts_gpt", "financial_tables_gpt"]:
        df[col] = df[col].apply(lambda x: "yes" if x else "no")

    # Add 'flagged_imp' column
    # Add 'flagged_imp' column
    df["flagged_imp"] = df.apply(
        lambda row: "yes" if (
            (row["charts_gpt"] == "yes") ^ (row["financial_tables_gpt"] == "yes")
        ) else "no", axis=1
    )


    # Drop raw detection columns
    df.drop(columns=["infographics", "charts", "financial_tables"], inplace=True)

    # Filter out rows where all GPT flags are 'no'
    df = df[~((df["infographics_gpt"] == "no") & 
            (df["charts_gpt"] == "no") & 
            (df["financial_tables_gpt"] == "no"))]




    df["pdf_summary"] = pdf_summary

    # Save locally to drive_outputs/
    output_folder = "drive_outputs"
    os.makedirs(output_folder, exist_ok=True)
    output_csv = os.path.join(output_folder, os.path.basename(pdf_path).replace(".pdf", "_gpt4o_summary.csv"))
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Results saved to CSV: {output_csv}")

    # Upload to Google Drive
    try:
        service_account_file = "turing-genai-ws-58339643dd3f.json"  # your service account JSON path
        folder_id = "1zRSbrOpugIJBPpw2aTsjYGRJcPIEZMJh"  # replace with your real folder ID
        file_id = upload_file_to_drive(service_account_file, output_csv, folder_id)
        print(f"✅ Uploaded to Google Drive: file ID = {file_id}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

