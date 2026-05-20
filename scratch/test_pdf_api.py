from pathlib import Path

from openai import OpenAI

client = OpenAI()

TEST_FILES = [
    "Order 1.pdf",
    "Prescription 1.pdf",
    "Sleep Study Report 1.pdf",
    "Physician Notes 1.pdf",
]


def classify_pdf(filename: str) -> None:
    """Upload and classify a single PDF."""
    path = Path("documents") / filename

    print()
    print("=" * 80)
    print(f"TESTING: {filename}")
    print("=" * 80)

    uploaded_file = client.files.create(
        file=open(path, "rb"),
        purpose="user_data",
    )

    print(f"Uploaded file id: {uploaded_file.id}")

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": uploaded_file.id,
                    },
                    {
                        "type": "input_text",
                        "text": """
                        What type of DME medical document is this?

                        Possible document types:
                        - Prescription
                        - Sleep Study Report
                        - Compliance Report
                        - Delivery Ticket
                        - Physician Notes
                        - Order

                        Return only the document type.
                        """,
                    },
                ],
            }
        ],
    )

    print()
    print("MODEL RESPONSE:")
    print(response.output_text.strip())


for pdf in TEST_FILES:
    classify_pdf(pdf)