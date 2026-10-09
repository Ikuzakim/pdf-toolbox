from pathlib import Path
import tempfile
import zipfile
import os
import uuid
import httpx


from core.auth.database import get_connection
from core.auth.auth import (
    authenticate_user,
    get_user_by_api_token,
    create_api_token,
)
from core.usage_tracker import (
    can_use,
    record_operation,
)
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import Response, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

load_dotenv()

from core.pdf.operations import (
    merge_pdfs,
    split_pdf,
    compress_pdf,
    reorder_pages,
    rotate_pdf,
    images_to_pdf,
)


app = FastAPI(
    title="PDF Toolbox API",
    version="1.0.0",
    description="API for PDF Toolbox operations.",
)
@app.exception_handler(Exception)
async def handle_unexpected_error(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred while processing the request."
        },
    )

bearer_scheme = HTTPBearer(
    auto_error=False
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Bearer authentication required.",
        )

    user = get_user_by_api_token(
        credentials.credentials
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API token.",
        )

    return user

PRO_TOOLS = {
    "Compress PDF",
    "Reorder / Delete Pages",
}


def authorize_operation(user, tool_name):
    if tool_name in PRO_TOOLS:
        if user["plan"] != "pro":
            raise HTTPException(
                status_code=403,
                detail=f"{tool_name} is a Pro feature.",
            )

    if not can_use(user):
        raise HTTPException(
            status_code=429,
            detail="Monthly operation limit reached.",
        )

async def read_upload_with_limit(uploaded_file):
    data = await uploaded_file.read()

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Uploaded file exceeds the 200 MB limit.",
        )

    return data
    
PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"

PAYSTACK_PRO_PLAN_CODE = os.getenv("PAYSTACK_PRO_PLAN_CODE")
PAYSTACK_AMOUNT = 70000  # KSh 700.00 in Paystack's smallest currency unit
PAYSTACK_CURRENCY = "KES"
MAX_UPLOAD_SIZE = 200 * 1024 * 1024

class APILoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def api_login(payload: APILoginRequest):
    user = authenticate_user(
        payload.email,
        payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    token = create_api_token(
        user["id"]
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_days": 30,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "plan": user["plan"],
            "subscription_status": user["subscription_status"],
        },
    }


class PaymentInitializeRequest(BaseModel):
    callback_url: str | None = None


@app.post("/payments/initialize")
async def initialize_payment(
    payload: PaymentInitializeRequest,
    current_user: dict = Depends(get_current_user),
):
    secret_key = os.getenv("PAYSTACK_SECRET_KEY")
    plan_code = os.getenv("PAYSTACK_PRO_PLAN_CODE")

    if not secret_key or not plan_code:
        raise HTTPException(
            status_code=500,
            detail="Paystack is not configured."
        )

    reference = f"pdf_toolbox_{uuid.uuid4().hex}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO payments (
                user_id,
                reference,
                amount,
                currency,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                current_user["id"],
                reference,
                PAYSTACK_AMOUNT,
                PAYSTACK_CURRENCY,
                "pending",
            ),
        )

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    data = {
        "email": current_user["email"],
        "currency": PAYSTACK_CURRENCY,
        "reference": reference,
        "plan": plan_code,
        "metadata": {
            "user_id": current_user["id"],
            "product": "pdf_toolbox_pro",
        },
    }

    if payload.callback_url:
        data["callback_url"] = payload.callback_url

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                PAYSTACK_INITIALIZE_URL,
                headers=headers,
                json=data,
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Paystack."
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Paystack error {response.status_code}: {response.text}"
        )

    result = response.json()

    if not result.get("status"):
        raise HTTPException(
            status_code=502,
            detail=result.get(
                "message",
                "Paystack transaction initialization failed."
            )
        )

    payment = result["data"]

    return {
        "authorization_url": payment["authorization_url"],
        "reference": payment["reference"],
        "amount": PAYSTACK_AMOUNT,
        "currency": PAYSTACK_CURRENCY,
        "plan_code": plan_code,
    }


@app.get("/payments/verify/{reference}")
async def verify_payment(
    reference: str,
    current_user: dict = Depends(get_current_user),
):
    secret_key = os.getenv("PAYSTACK_SECRET_KEY")

    if not secret_key:
        raise HTTPException(
            status_code=500,
            detail="Paystack is not configured."
        )

    # Find the payment we created during initialization.
    with get_connection() as connection:
        payment = connection.execute(
            """
            SELECT
                id,
                user_id,
                reference,
                amount,
                currency,
                status,
                paid_at
            FROM payments
            WHERE reference = ?
            """,
            (reference,),
        ).fetchone()

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment reference not found."
        )
    if payment["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to verify this payment."
        )

    # Idempotency: if we already processed this payment,
    # return the existing state instead of processing it again.
    if payment["status"] == "success":
        return {
            "reference": payment["reference"],
            "status": "success",
            "amount": payment["amount"],
            "currency": payment["currency"],
            "paid_at": payment["paid_at"],
            "plan": "pro",
            "subscription_status": "active",
        }

    headers = {
        "Authorization": f"Bearer {secret_key}",
    }

    url = f"https://api.paystack.co/transaction/verify/{reference}"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                url,
                headers=headers,
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to Paystack."
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="Paystack verification failed."
        )

    result = response.json()

    if not result.get("status"):
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "message",
                "Payment verification failed."
            )
        )

    transaction = result["data"]

    # Verify the transaction itself.
    if transaction.get("status") != "success":
        return {
            "reference": transaction.get("reference"),
            "status": transaction.get("status"),
            "amount": transaction.get("amount"),
            "currency": transaction.get("currency"),
            "paid_at": transaction.get("paid_at"),
            "plan": "free",
            "subscription_status": "inactive",
        }

    # Verify the transaction matches what we expected.
    if transaction.get("reference") != payment["reference"]:
        raise HTTPException(
            status_code=400,
            detail="Payment reference mismatch."
        )

    if transaction.get("amount") != PAYSTACK_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail="Payment amount mismatch."
        )

    if transaction.get("currency") != PAYSTACK_CURRENCY:
        raise HTTPException(
            status_code=400,
            detail="Payment currency mismatch."
        )

    paid_at = transaction.get("paid_at")

    # Record successful payment and activate Pro atomically.
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE payments
            SET
                status = ?,
                paid_at = ?
            WHERE id = ?
            """,
            (
                "success",
                paid_at,
                payment["id"],
            ),
        )

        connection.execute(
            """
            UPDATE users
            SET
                plan = ?,
                subscription_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                "pro",
                "active",
                payment["user_id"],
            ),
        )

    return {
        "reference": transaction["reference"],
        "status": transaction["status"],
        "amount": transaction["amount"],
        "currency": transaction["currency"],
        "paid_at": paid_at,
        "plan": "pro",
        "subscription_status": "active",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "PDF Toolbox API",
        "version": "1.0.0",
    }


@app.post(
    "/merge",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "format": "binary",
                                },
                            }
                        },
                        "required": ["files"],
                    }
                }
            }
        }
    },
)
async def merge_pdf_endpoint(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    authorize_operation(
        current_user,
        "Merge PDF",
    )
    if len(files) < 2:
        return {
            "error": "At least 2 PDF files are required."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_paths = []

        for index, uploaded_file in enumerate(files):
            input_path = temp_path / f"input_{index}.pdf"

            content = await read_upload_with_limit(uploaded_file)

            with open(input_path, "wb") as output_file:
                output_file.write(content)

            input_paths.append(input_path)

        output_path = temp_path / "merged_result.pdf"

        merge_pdfs(
            input_paths,
            output_path,
        )

        pdf_bytes = output_path.read_bytes()

    record_operation(current_user)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="merged_result.pdf"'
        },
    )


@app.post("/split")
async def split_pdf_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    authorize_operation(
        current_user,
        "Split PDF",
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"

        content = await read_upload_with_limit(file)

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        import pymupdf

        document = pymupdf.open(input_path)
        page_count = len(document)
        document.close()

        output_dir = temp_path / "split_pages"
        output_dir.mkdir()

        output_paths = [
            output_dir / f"page_{page_number + 1}.pdf"
            for page_number in range(page_count)
        ]

        split_pdf(
            input_path,
            output_paths,
        )

        zip_path = temp_path / "split_result.zip"

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as zip_file:
            for pdf_file in output_paths:
                zip_file.write(
                    pdf_file,
                    arcname=pdf_file.name,
                )

        zip_bytes = zip_path.read_bytes()
    
    record_operation(current_user)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="split_result.zip"'
        },
    )


@app.post("/compress")
async def compress_pdf_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    authorize_operation(
        current_user,
        "Compress PDF",
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"
        output_path = temp_path / "compressed_result.pdf"

        content = await read_upload_with_limit(file)

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        compress_pdf(
            input_path,
            output_path,
        )

        pdf_bytes = output_path.read_bytes()

    record_operation(current_user)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="compressed_result.pdf"'
        },
    )


@app.post("/reorder-delete")
async def reorder_delete_pdf_endpoint(
    file: UploadFile = File(...),
    page_order: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    authorize_operation(
        current_user,
        "Reorder / Delete Pages",
    )
    try:
        page_indexes = [
            int(index.strip())
            for index in page_order.split(",")
            if index.strip()
        ]
    except ValueError:
        return {
            "error": "page_order must contain comma-separated page numbers."
        }

    if not page_indexes:
        return {
            "error": "At least one page index is required."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"
        output_path = temp_path / "reordered_result.pdf"

        content = await read_upload_with_limit(file)

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        try:
            reorder_pages(
                input_path,
                output_path,
                page_indexes,
            )
        except ValueError as error:
            return {
                "error": str(error)
            }

        pdf_bytes = output_path.read_bytes()

    record_operation(current_user)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="reordered_result.pdf"'
        },
    )


@app.post("/rotate")
async def rotate_pdf_endpoint(
    file: UploadFile = File(...),
    rotation: int = Form(90),
    current_user: dict = Depends(get_current_user),
):
    authorize_operation(
        current_user,
        "Rotate PDF",
    )
    if rotation not in (90, 180, 270):
        return {
            "error": "Rotation must be 90, 180, or 270 degrees."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "input.pdf"
        output_path = temp_path / "rotated_result.pdf"

        content = await read_upload_with_limit(file)

        with open(input_path, "wb") as output_file:
            output_file.write(content)

        rotate_pdf(
            input_path,
            output_path,
            rotation,
        )

        pdf_bytes = output_path.read_bytes()

    record_operation(current_user)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rotated_result.pdf"'
        },
    )


@app.post(
    "/images-to-pdf",
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "format": "binary",
                                },
                            }
                        },
                        "required": ["files"],
                    }
                }
            }
        }
    },
)
async def images_to_pdf_endpoint(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    authorize_operation(
        current_user,
        "Images → PDF",
    )
    if not files:
        return {
            "error": "At least one image is required."
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_paths = []

        for index, uploaded_file in enumerate(files):
            suffix = Path(uploaded_file.filename or "").suffix or ".jpg"

            input_path = temp_path / f"image_{index}{suffix}"

            content = await read_upload_with_limit(uploaded_file)

            with open(input_path, "wb") as output_file:
                output_file.write(content)

            input_paths.append(input_path)

        output_path = temp_path / "images_to_pdf_result.pdf"

        images_to_pdf(
            input_paths,
            output_path,
        )

        pdf_bytes = output_path.read_bytes()

    record_operation(current_user)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="images_to_pdf_result.pdf"'
        },
    )