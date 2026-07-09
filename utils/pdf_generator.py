import json
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _draw_section_title(c: canvas.Canvas, title: str, x: float, y: float) -> float:
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#2563eb"))
    c.drawString(x, y, title)
    return y - 16


def _draw_wrapped_text(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, leading: float = 14):
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    for line in text.split("\n"):
        words = line.split(" ")
        current = ""
        for word in words:
            test_line = f"{current} {word}".strip()
            if c.stringWidth(test_line, "Helvetica", 10) > max_width:
                c.drawString(x, y, current)
                y -= leading
                current = word
            else:
                current = test_line
        if current:
            c.drawString(x, y, current)
            y -= leading
    return y


def _draw_probability_chart(c: canvas.Canvas, probabilities: dict, x: float, y: float, width: float, height: float) -> float:
    c.setFillColor(colors.HexColor("#f4f7ff"))
    c.roundRect(x, y - height, width, height, 8, fill=1, stroke=0)

    max_value = max(probabilities.values()) if probabilities else 100
    bar_width = width / max(len(probabilities), 1)
    palette = [colors.HexColor(color) for color in ["#2563eb", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444"]]

    for index, (label, value) in enumerate(probabilities.items()):
        bar_height = (value / max_value) * (height - 20)
        left = x + index * bar_width + 8
        c.setFillColor(palette[index % len(palette)])
        c.roundRect(left, y - 16 - bar_height, bar_width - 16, bar_height, 4, fill=1, stroke=0)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.black)
        c.drawCentredString(left + (bar_width - 16) / 2, y - height + 6, label)
        c.drawCentredString(left + (bar_width - 16) / 2, y - 18 - bar_height, f"{value}%")

    return y - height - 12


def generate_pdf_report(buffer: BytesIO, report_data: dict) -> BytesIO:
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50
    current_y = height - margin

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.HexColor("#0b4a8f"))
    c.drawString(margin, current_y, "NutriSense AI")
    c.setFont("Helvetica", 12)
    header_date = report_data.get("assessment_date") or report_data.get("patient_info", {}).get("assessment_date", "")
    c.drawString(width - margin - 180, current_y, header_date)
    current_y -= 28

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, current_y, "Health Assessment Report")
    current_y -= 22
    c.setStrokeColor(colors.HexColor("#dbeafe"))
    c.setLineWidth(1)
    c.line(margin, current_y, width - margin, current_y)
    current_y -= 18

    patient = report_data.get("patient_info", {})
    left_col = margin
    right_col = width / 2 + 10
    current_y = _draw_section_title(c, "Patient Information", left_col, current_y)
    patient_lines = [
        f"Name: {patient.get('name', 'N/A')}",
        f"Age: {patient.get('age', 'N/A')}",
        f"Gender: {patient.get('gender', 'N/A')}",
        f"Email: {patient.get('email', 'N/A')}",
    ]
    for line in patient_lines:
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(left_col, current_y, line)
        current_y -= 14

    current_y -= 10
    _draw_section_title(c, "Predicted Deficiency", right_col, current_y + 10)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_col, current_y - 10, report_data.get("predicted_deficiency", "Unknown"))
    c.setFont("Helvetica", 10)
    c.drawString(right_col, current_y - 26, f"Confidence: {report_data.get('confidence_score', 0)}%")
    current_y -= 42

    current_y = _draw_section_title(c, "Probability Breakdown", left_col, current_y)
    current_y = _draw_probability_chart(c, report_data.get("probabilities", {}), left_col, current_y, width - margin * 2, 120)

    current_y -= 4
    current_y = _draw_section_title(c, "Symptoms Summary", left_col, current_y)
    current_y = _draw_wrapped_text(c, report_data.get("symptoms_summary", "Not available."), left_col, current_y, width - margin * 2)
    current_y -= 6

    current_y = _draw_section_title(c, "Lifestyle Summary", left_col, current_y)
    current_y = _draw_wrapped_text(c, report_data.get("lifestyle_summary", "Not available."), left_col, current_y, width - margin * 2)
    current_y -= 6

    def _draw_list_section(header: str, items: list[str], x: float, y: float):
        y = _draw_section_title(c, header, x, y)
        for item in items:
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.black)
            c.drawString(x + 8, y, f"• {item}")
            y -= 14
        return y

    current_y = _draw_list_section("Foods to Eat", report_data.get("foods_to_eat", []), left_col, current_y)
    current_y -= 6
    current_y = _draw_list_section("Foods to Avoid", report_data.get("foods_to_limit", []), left_col, current_y)
    current_y -= 6
    current_y = _draw_list_section("Lifestyle Recommendations", report_data.get("lifestyle_recommendations", []), left_col, current_y)

    current_y -= 12
    current_y = _draw_section_title(c, "Disclaimer", left_col, current_y)
    current_y = _draw_wrapped_text(c, report_data.get("disclaimer", "This report is for educational purposes only."), left_col, current_y, width - margin * 2)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
