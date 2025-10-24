from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List
from datetime import datetime
from fpdf import FPDF
import io

from security import get_current_user
from database import db
from models import TestCase, DomainGroup, GenerateResponse

router = APIRouter()

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Compliance Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

@router.post("/api/reports/compliance", tags=["Reporting"], summary="Generate Compliance Report",
    description="Generates a compliance report in PDF format based on finalized test cases.")
async def generate_compliance_report(user: Dict[str, Any] = Depends(get_current_user)):
    try:
        user_id = user['uid']
        docs_ref = db.collection('users').document(user_id).collection('finalized_test_cases')
        docs = docs_ref.stream()

        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        for doc in docs:
            doc_data = doc.to_dict()
            product_name = doc_data.get('product_name', 'N/A')
            requirement = doc_data.get('requirement', 'N/A')
            domains = doc_data.get('domains', [])

            pdf.chapter_title(f"Product: {product_name}")
            pdf.chapter_body(f"Requirement: {requirement}")

            for domain_group in domains:
                domain_name = domain_group.get('domain', 'N/A')
                test_cases = domain_group.get('test_cases', [])

                pdf.chapter_title(f"  Domain: {domain_name}")
                for tc_data in test_cases:
                    test_case = TestCase(**tc_data)
                    pdf.chapter_body(f"    Test Case ID: {test_case.test_case_id}")
                    pdf.chapter_body(f"    Title: {test_case.title}")
                    pdf.chapter_body(f"    Type: {test_case.type}")
                    pdf.chapter_body(f"    Priority: {test_case.priority}")
                    pdf.chapter_body(f"    Compliance Tag: {test_case.compliance_tag}")
                    pdf.chapter_body(f"    Traceability ID: {test_case.traceability_id}")
                    pdf.chapter_body(f"    Steps: {test_case.steps}")
                    pdf.ln(5)

        pdf_output = pdf.output(dest='S').encode('latin-1')

        return StreamingResponse(io.BytesIO(pdf_output),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=\"compliance_report.pdf\""
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))