from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pygments import highlight
from pygments.lexers import JavaLexer, PythonLexer
from pygments.formatters import HtmlFormatter
from bs4 import BeautifulSoup
from openai import OpenAI

class CodeToPDF:
    def __init__(self, default_prefix="output"):
        self.default_prefix = default_prefix

    def _unique_filename(self) -> str:
        """Generate a unique filename with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return f"{self.default_prefix}_{timestamp}.pdf"


    def convert(self, code_input: str) -> str:
        try:
            filename = self._unique_filename()
            styles = getSampleStyleSheet()
            doc = SimpleDocTemplate(filename, pagesize=letter)

            code_style = ParagraphStyle(
                "CodeStyle",
                fontName="Courier",
                fontSize=9,
                leading=11,
                leftIndent=20
            )
            story = [Preformatted(code_input,style=code_style)]
            doc.build(story)

            return f"✅ PDF created successfully: {filename}"
        except Exception as e:
            return f"❌ Error creating PDF: {str(e)}"


if __name__ == "__main__":
    sample_code = """
        public class HelloWorld {
            public static void main(String[] args) {
                System.out.println("Hello, World!");
            }
        }
        """
    toPDF = CodeToPDF()
    toPDF.convert(sample_code)