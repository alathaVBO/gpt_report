import pandas as pd
import os
import xlsxwriter

# load .env variables
from dotenv import load_dotenv
import uuid
load_dotenv()

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
RESULTS_FOLDER = os.getenv('RESULTS_FOLDER')

# os.walk traverse all files in path, and return a tuple
path_upload, dirs_upload, files_upload = next(os.walk(UPLOAD_FOLDER))
upload_file_count = len(files_upload)


def generate_report():
    df = pd.DataFrame()

    for file in range(upload_file_count):
        # Load the Excel file
        try:
            df = pd.read_excel(UPLOAD_FOLDER + files_upload[file])
        except Exception as e:
            try:
                df = pd.read_csv(UPLOAD_FOLDER + files_upload[file], sep=',', header=0)
            except Exception as e:
                print(e)

        # Keep relevant columns and drop rows with missing 'Merchant' or 'Status'
        df = df[['Merchant', 'MID', 'Transaction Date', 'Status', 'Amount', 'Payer Country', 'Brand', 'Issuer',
                 'Decline reason']]
        df = df.dropna(subset=['Merchant', 'Status'])

        # Group data by Merchant and MID
        grouped_data = df.groupby(['Merchant', 'MID'])

        # Initialize a dictionary to hold data for each merchant
        final_merchant_data = {}

        # Iterate through each group to generate reports
        for (merchant, mid), group_df in grouped_data:
            merchant_mid_data = []

            # Calculate approved, failed transactions and their ratio
            status_count = group_df['Status'].value_counts()
            approved_count = status_count.get('success', 0)
            failed_count = status_count.get('fail', 0)
            total_count = approved_count + failed_count
            approval_ratio = approved_count / total_count if total_count > 0 else 0
            summary_df = pd.DataFrame({
                'Metric': ['Total Transactions', 'Approved Transactions', 'Failed Transactions', 'Approval Ratio',
                           'Total Amount', 'Total Approved Amount'],
                'Value': [total_count, approved_count, failed_count, approval_ratio, group_df['Amount'].sum(),
                          group_df[group_df['Status'] == 'success']['Amount'].sum()]
            })
            merchant_mid_data.append(('MID Summary', summary_df))

            # Summarize decline reasons (if available)
            if 'Decline reason' in group_df.columns:
                decline_reasons = group_df[group_df['Status'] == 'fail']['Decline reason'].value_counts().reset_index()
                decline_reasons.columns = ['Decline Reason', 'Count']
                merchant_mid_data.append(('Decline Summary', decline_reasons))

            # Summarize payer countries
            country_summary = group_df['Payer Country'].value_counts().reset_index()
            country_summary.columns = ['Country', 'Count']
            country_approval_ratio = group_df.groupby('Payer Country')['Status'].apply(
                lambda x: (x == 'success').sum() / len(x)).reset_index()
            country_approval_ratio.columns = ['Country', 'Approval Ratio']
            country_summary = pd.merge(country_summary, country_approval_ratio, on='Country', how='left')
            merchant_mid_data.append(('Country Summary', country_summary))

            # Card brand summary
            card_brand_summary = group_df.groupby('Brand')['Status'].apply(
                lambda x: (x == 'success').sum() / len(x)).reset_index()
            card_brand_summary.columns = ['Card Brand', 'Approval Ratio']
            merchant_mid_data.append(('Card Brand Summary', card_brand_summary))

            # Issuer summary
            issuer_summary = group_df['Issuer'].value_counts().reset_index()
            issuer_summary.columns = ['Issuer', 'Count']
            merchant_mid_data.append(('Issuer Summary', issuer_summary))

            # Adding the underlying data to the report content
            merchant_mid_data.append(('Underlying Data', group_df))

            final_merchant_data[(merchant, mid)] = merchant_mid_data

        # Generate Excel report with underlying data
        unique_id = str(uuid.uuid4())
        output_file_path = f'Merchant_MID_Report_{unique_id}.xlsx'
        with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
            existing_sheets = set()  # To track existing sheet names
            for (merchant, mid), content in final_merchant_data.items():
                sheet_name = f"{merchant}_{mid}".replace(" ", "_")[:31]  # Limit to 31 characters for Excel sheet names

                # Add a suffix if sheet name already exists
                suffix = 1
                original_sheet_name = sheet_name
                while sheet_name in existing_sheets:
                    sheet_name = f"{original_sheet_name}_{suffix}".replace(" ", "_")[:31]
                    suffix += 1
                existing_sheets.add(sheet_name)

                workbook = writer.book
                worksheet = workbook.add_worksheet(sheet_name)
                row = 0
                title_format = workbook.add_format({'bold': True, 'bg_color': '#ADD8E6', 'border': 1, 'align': 'center'})
                header_format = workbook.add_format({'bold': True, 'bg_color': '#F0E68C', 'border': 1, 'align': 'center'})
                cell_format = workbook.add_format({'border': 1})
                percent_format = workbook.add_format({'num_format': '0.00%', 'border': 1})
                for title, df in content:
                    worksheet.merge_range(row, 0, row, len(df.columns) - 1, title, title_format)
                    row += 1
                    for c_idx, column_name in enumerate(df.columns, start=0):
                        worksheet.write(row, c_idx, column_name, header_format)
                    for r_idx, df_row in enumerate(df.values, start=row + 1):
                        for c_idx, value in enumerate(df_row, start=0):
                            # Check and replace NaN or INF values with an empty string
                            if pd.isna(value) or value == float('inf') or value == float('-inf'):
                                value = ""
                            if isinstance(value, float) and 0 <= value <= 1:
                                worksheet.write(r_idx, c_idx, value, percent_format)
                            else:
                                worksheet.write(r_idx, c_idx, value, cell_format)
                    row += len(df) + 2


if __name__ == "__main__":
    generate_report()
