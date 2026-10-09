import os
import streamlit as st
import pymupdf
import httpx

from core.pdf.operations import (
    merge_pdfs,
    split_pdf,
    compress_pdf,
    reorder_pages,
    rotate_pdf,
    images_to_pdf,
)

from core.file_manager import (
    create_workspace,
    cleanup_workspace,
)

from core.auth.auth import (
    create_user,
    authenticate_user,
)

from core.usage_tracker import (
    can_use,
    record_operation,
    get_usage,
    get_remaining_operations,
)


try:
    PAYMENT_API_URL = st.secrets["PAYMENT_API_URL"]
except (KeyError, FileNotFoundError):
    PAYMENT_API_URL = os.getenv(
        "PAYMENT_API_URL",
        "http://127.0.0.1:8000",
    )

def api_login(email, password):
    response = httpx.post(
        f"{PAYMENT_API_URL}/auth/login",
        json={
            "email": email,
            "password": password,
        },
        timeout=20.0,
    )

    response.raise_for_status()

    return response.json()


def initialize_payment(user):
    response = httpx.post(
        f"{PAYMENT_API_URL}/payments/initialize",
        headers={
            "Authorization": f"Bearer {st.session_state.api_token}",
        },
        json={},
        timeout=20.0,
    )

    response.raise_for_status()

    return response.json()


def verify_payment(reference):
    response = httpx.get(
        f"{PAYMENT_API_URL}/payments/verify/{reference}",
        headers={
            "Authorization": f"Bearer {st.session_state.api_token}",
        },
        timeout=20.0,
    )

    response.raise_for_status()

    return response.json()


st.set_page_config(
    page_title="PDF Toolbox",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def initialize_session():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user" not in st.session_state:
        st.session_state.user = None

    if "api_token" not in st.session_state:
        st.session_state.api_token = None

    if "checkout_reference" not in st.session_state:
        st.session_state.checkout_reference = None

    if "checkout_url" not in st.session_state:
        st.session_state.checkout_url = None

def start_pro_checkout():
    user = st.session_state.user

    try:
        checkout = initialize_payment(user)

        st.session_state.checkout_reference = checkout["reference"]
        st.session_state.checkout_url = checkout["authorization_url"]

        return checkout

    except httpx.HTTPError as error:
        st.error(
            "We couldn't start the payment. "
            "Please try again."
        )
        return None
    
initialize_session()


def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.api_token = None
    st.session_state.selected_tool = None


def show_auth():
    st.markdown(
        """
        <style>
            .auth-container {
                max-width: 430px;
                margin: 5rem auto 0 auto;
            }

            .auth-title {
                text-align: center;
                font-size: 2rem;
                font-weight: 800;
                letter-spacing: -0.04em;
                margin-bottom: 0.5rem;
            }

            .auth-copy {
                text-align: center;
                opacity: 0.6;
                margin-bottom: 2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="auth-container">
            <div class="auth-title">PDF Toolbox</div>
            <div class="auth-copy">
                Sign in to continue
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(
        ["Log in", "Create account"]
    )

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input(
                "Password",
                type="password",
            )

            submitted = st.form_submit_button(
                "Log in",
                use_container_width=True,
            )

            if submitted:
                if not email or not password:
                    st.error("Enter your email and password.")
                else:
                    user = authenticate_user(
                        email,
                        password,
                    )

                    if user is None:
                        st.error(
                            "Invalid email or password."
                        )
                    else:
                        try:
                            api_session = api_login(
                                email,
                                password,
                            )

                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.api_token = (
                                api_session["access_token"]
                            )

                            st.rerun()

                        except httpx.HTTPError:
                            st.error(
                                "Unable to connect to the payment service."
                            )


    with tab_register:
        with st.form("register_form"):
            email = st.text_input(
                "Email",
                key="register_email",
            )

            password = st.text_input(
                "Password",
                type="password",
                key="register_password",
            )

            confirm_password = st.text_input(
                "Confirm password",
                type="password",
            )

            submitted = st.form_submit_button(
                "Create account",
                use_container_width=True,
            )

            if submitted:
                if not email or not password:
                    st.error(
                        "Enter an email and password."
                    )

                elif password != confirm_password:
                    st.error(
                        "Passwords do not match."
                    )

                elif len(password) < 8:
                    st.error(
                        "Password must be at least 8 characters."
                    )

                else:
                    user = create_user(
                        email,
                        password,
                    )

                    if user is None:
                        st.error(
                            "An account with that email already exists."
                        )

                    else:
                        st.session_state.authenticated = True
                        st.session_state.user = user

                        st.success(
                            "Account created successfully."
                        )

                        st.rerun()

if not st.session_state.authenticated:
    show_auth()
    st.stop()


TOOL_DEFINITIONS = {
    "Merge PDF": {
        "icon": "↔",
        "description": "Combine multiple PDF files into one.",
        "access": "FREE",
    },
    "Split PDF": {
        "icon": "✂",
        "description": "Extract pages from a PDF.",
        "access": "FREE",
    },
    "Compress PDF": {
        "icon": "↓",
        "description": "Reduce file size for easier sharing.",
        "access": "PRO",
    },
    "Reorder / Delete Pages": {
        "icon": "☷",
        "description": "Rearrange or remove unwanted pages.",
        "access": "PRO",
    },
    "Rotate PDF": {
        "icon": "↻",
        "description": "Turn PDF pages to the correct orientation.",
        "access": "FREE",
    },
    "Images → PDF": {
        "icon": "▧",
        "description": "Turn images into a single PDF.",
        "access": "FREE",
    },
}

#--------------------------------------------------
# Account view State
#--------------------------------------------------
if "selected_tool" not in st.session_state:
    st.session_state.selected_tool = None

if "current_view" not in st.session_state:
    st.session_state.current_view = "home"


def select_tool(tool_name):
    st.session_state.selected_tool = tool_name


def show_account():
    user = st.session_state.user

    st.markdown(
        """
        <style>
            .account-container {
                max-width: 760px;
                margin: 2rem auto 0 auto;
            }

            .account-kicker {
                font-size: 0.82rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                opacity: 0.55;
                margin-bottom: 0.5rem;
            }

            .account-title {
                font-size: 2.4rem;
                font-weight: 800;
                letter-spacing: -0.045em;
                margin-bottom: 0.35rem;
            }

            .account-email {
                opacity: 0.6;
                margin-bottom: 2.5rem;
            }

            .account-section {
                padding: 1.25rem 0;
                border-top: 1px solid rgba(128,128,128,0.20);
            }

            .account-label {
                font-size: 0.78rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.07em;
                opacity: 0.55;
                margin-bottom: 0.35rem;
            }

            .account-value {
                font-size: 1.15rem;
                font-weight: 650;
            }

            .account-muted {
                opacity: 0.6;
                font-size: 0.92rem;
                margin-top: 0.2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="account-container">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="account-kicker">Account</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="account-title">Your account</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="account-email">{user["email"]}</div>',
        unsafe_allow_html=True,
    )

    if user["plan"] == "pro":
        plan_name = "Pro"
        plan_detail = "KSh 700/month"
        plan_status = "Active"
        usage_limit = 150
    else:
        plan_name = "Free"
        plan_detail = "10 operations/month"
        plan_status = "Active"
        usage_limit = 10

    remaining = get_remaining_operations(user)
    used = usage_limit - remaining

    st.markdown(
        f"""
        <div class="account-section">
            <div class="account-label">Plan</div>
            <div class="account-value">{plan_name}</div>
            <div class="account-muted">{plan_detail} · {plan_status}</div>
        </div>

        <div class="account-section">
            <div class="account-label">Usage</div>
            <div class="account-value">
                {remaining} of {usage_limit} operations remaining
            </div>
            <div class="account-muted">
                {used} operation{"s" if used != 1 else ""} used this month
            </div>
        </div>

        <div class="account-section">
            <div class="account-label">Billing</div>
            <div class="account-value">
                {"Pro subscription" if user["plan"] == "pro" else "Free plan"}
            </div>
            <div class="account-muted">
                {"KSh 700/month" if user["plan"] == "pro" else "Upgrade to Pro for more operations"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    action_col, _ = st.columns([1, 3])

    with action_col:
        if st.button(
            "← Back to PDF Toolbox",
            use_container_width=True,
            key="back_to_home",
        ):
            st.session_state.current_view = "home"
            st.rerun()

    st.divider()

    if st.button(
        "Log out",
        use_container_width=True,
        key="account_logout",
    ):
        logout()
        st.rerun()


# --------------------------------------------------
# HOME
# --------------------------------------------------
def show_home():
    user = st.session_state.user

    topbar_action = st.columns([4, 1])

    with topbar_action[1]:
        if st.button(
            "👤",
            help="Account",
            use_container_width=True,
            key="account_button",
        ):
            st.session_state.current_view = "account"
            st.rerun()

    usage = get_usage(user)
    remaining = get_remaining_operations(user)
    if user["plan"] == "pro":
        st.success(
            "PDF Toolbox Pro · 150 operations/month"
        )
    else:
        st.info(
            "PDF Toolbox Free · "
            f"{remaining} of 10 operations remaining"
        )

        if st.button(
            "Upgrade to Pro · KSh 700/month",
            use_container_width=True,
            key="upgrade_pro_home",
        ):
            checkout = start_pro_checkout()

            if checkout:
                st.session_state.checkout_url = (
                    checkout["authorization_url"]
                )
                st.rerun()

    if st.session_state.checkout_url:
        st.divider()

        st.subheader("Complete your Pro upgrade")

        st.write(
            "You're upgrading to PDF Toolbox Pro "
            "for KSh 700/month."
        )

        st.link_button(
            "Continue to secure payment",
            st.session_state.checkout_url,
            use_container_width=True,
        )

        st.caption(
            "After completing payment, return here and verify your payment."
        )

        if st.button(
            "I've completed payment",
            use_container_width=True,
            key="payment_completed",
        ):
            try:
                verification = verify_payment(
                    st.session_state.checkout_reference
                )

                if verification["status"] == "success":
                    st.session_state.checkout_url = None
                    st.session_state.checkout_reference = None

                    # Refresh the authenticated user's database record.
                    from core.auth.auth import get_user_by_id

                    user = get_user_by_id(
                        st.session_state.user["id"]
                    )

                    st.session_state.user = user

                    st.success(
                        "🎉 Payment verified. "
                        "PDF Toolbox Pro is now active."
                    )

                    st.rerun()

                else:
                    st.warning(
                        "Payment has not been confirmed yet. "
                        "Complete the payment and try again."
                    )

            except httpx.HTTPError:
                st.error(
                    "We couldn't verify the payment yet. "
                    "Please try again."
                )

    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1120px;
                padding-top: 2.25rem;
                padding-bottom: 3.5rem;
            }

            .topbar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 3.25rem;
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 0.7rem;
                font-size: 1.30rem;
                font-weight: 750;
                letter-spacing: -0.02em;
            }

            .brand-mark {
                width: 34px;
                height: 34px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid rgba(128,128,128,0.28);
                border-radius: 9px;
                font-size: 1rem;
            }

            .usage-pill {
                padding: 0.52rem 0.9rem;
                border: 1px solid rgba(128,128,128,0.25);
                border-radius: 999px;
                font-size: 0.94rem;
                font-weight: 650;
                opacity: 0.78;
                white-space: nowrap;
            }

            .hero {
                max-width: 760px;
                margin: 0 auto 3rem auto;
                text-align: center;
            }

            .eyebrow {
                font-size: 0.76rem;
                font-weight: 750;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                opacity: 0.55;
                margin-bottom: 0.85rem;
            }

            .hero-title {
                font-size: clamp(2.25rem, 5vw, 4rem);
                line-height: 1.02;
                font-weight: 800;
                letter-spacing: -0.055em;
                margin: 0 0 1rem 0;
            }

            .hero-copy {
                font-size: 1.05rem;
                line-height: 1.65;
                opacity: 0.66;
                max-width: 650px;
                margin: 0 auto;
            }

            .tool-heading {
                font-size: 0.78rem;
                font-weight: 750;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                opacity: 0.5;
                margin: 0 0 0.9rem 0;
            }

            .tool-card {
                min-height: 176px;
                padding: 1.35rem 1.3rem 1.05rem 1.3rem;
                border: 1px solid rgba(128,128,128,0.23);
                border-radius: 16px;
                background: rgba(128,128,128,0.025);
            }

            .tool-icon {
                width: 38px;
                height: 38px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid rgba(128,128,128,0.22);
                border-radius: 10px;
                font-size: 1.15rem;
                margin-bottom: 1rem;
            }

            .tool-title {
                font-size: 1.02rem;
                font-weight: 750;
                letter-spacing: -0.015em;
                margin-bottom: 0.35rem;
            }

            .tool-description {
                min-height: 2.65rem;
                font-size: 0.86rem;
                line-height: 1.5;
                opacity: 0.62;
            }

            .tool-access {
                margin-top: 0.9rem;
                font-size: 0.68rem;
                font-weight: 800;
                letter-spacing: 0.1em;
                opacity: 0.55;
            }

            .pro-note {
                max-width: 760px;
                margin: 2.2rem auto 0 auto;
                padding: 1rem 1.2rem;
                border: 1px solid rgba(128,128,128,0.2);
                border-radius: 14px;
                text-align: center;
                font-size: 0.84rem;
                line-height: 1.5;
                opacity: 0.72;
            }

            .footer {
                margin-top: 4rem;
                padding-top: 1.25rem;
                border-top: 1px solid rgba(128,128,128,0.18);
                text-align: center;
                font-size: 0.75rem;
                opacity: 0.48;
            }

            div.stButton > button {
                border-radius: 9px;
                font-weight: 650;
            }

            div.stButton > button:hover {
                border-color: rgba(128,128,128,0.55);
            }

            @media (max-width: 700px) {
                .block-container {
                    padding-top: 1.25rem;
                    padding-left: 1rem;
                    padding-right: 1rem;
                }

                .topbar {
                    margin-bottom: 2.5rem;
                }

                .hero {
                    margin-bottom: 2.25rem;
                }

                .hero-title {
                    font-size: 2.35rem;
                }

                .usage-pill {
                    display: none;
                }

                .tool-card {
                    min-height: 0;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand">
                <div class="brand-mark">▣</div>
                <span>PDF Toolbox</span>
            </div>
            <div class="usage-pill">
                {user["plan"].title()} · {remaining} operations remaining
            </div>
        </div>

        <div class="hero">
            <div class="eyebrow">PDF work, made simple</div>
            <div class="hero-title">The essential tools for working with PDFs.</div>
            <div class="hero-copy">
                Merge, split, compress, organize, rotate, and convert —
                everything you need to get the PDF job done.
            </div>
        </div>

        <div class="tool-heading">Choose a tool</div>
        """,
        unsafe_allow_html=True,
    )

    tool_names = list(TOOL_DEFINITIONS.keys())

    for row_start in range(0, len(tool_names), 3):
        cols = st.columns(3, gap="medium")

        for col, tool_name in zip(
            cols,
            tool_names[row_start:row_start + 3],
        ):
            definition = TOOL_DEFINITIONS[tool_name]

            with col:
                st.markdown(
                    f"""
                    <div class="tool-card">
                        <div class="tool-icon">{definition["icon"]}</div>
                        <div class="tool-title">{tool_name}</div>
                        <div class="tool-description">
                            {definition["description"]}
                        </div>
                        <div class="tool-access">{definition["access"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.button(
                    f"Use {tool_name} →",
                    key=f"open_{tool_name}",
                    use_container_width=True,
                    on_click=select_tool,
                    args=(tool_name,),
                )

    st.markdown(
        """
        <div class="pro-note">
            <strong>PDF Toolbox Pro</strong> — expanded PDF capabilities and higher usage limits.
            Your free plan gives you 10 operations each month.
        </div>

        <div class="footer">
            PDF Toolbox · Professional PDF tools without the clutter.
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_tool_header(tool_name):
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 900px;
                padding-top: 2rem;
                padding-bottom: 3.5rem;
            }

            .tool-topbar {
                margin-bottom: 2.4rem;
            }

            .workspace-kicker {
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                opacity: 0.5;
                margin-bottom: 0.55rem;
            }

            .workspace-title {
                font-size: 2.2rem;
                line-height: 1.1;
                font-weight: 800;
                letter-spacing: -0.045em;
                margin-bottom: 0.5rem;
            }

            .workspace-copy {
                font-size: 0.96rem;
                line-height: 1.55;
                opacity: 0.62;
                max-width: 620px;
            }

            .workspace-footer {
                margin-top: 3.5rem;
                padding-top: 1.25rem;
                border-top: 1px solid rgba(128,128,128,0.18);
                text-align: center;
                font-size: 0.75rem;
                opacity: 0.48;
            }

            div.stButton > button {
                border-radius: 9px;
                font-weight: 650;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("← All tools", key="back_to_tools"):
        st.session_state.selected_tool = None
        st.rerun()

    definition = TOOL_DEFINITIONS[tool_name]

    st.markdown(
        f"""
        <div class="tool-topbar">
            <div class="workspace-kicker">{definition["access"]} · PDF TOOLBOX</div>
            <div class="workspace-title">{tool_name}</div>
            <div class="workspace-copy">{definition["description"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if st.session_state.current_view == "account":
    show_account()
    st.stop()

if st.session_state.selected_tool is None:
    show_home()
    st.stop()

tool = st.session_state.selected_tool
show_tool_header(tool)

user = st.session_state.user

# --------------------------------------------------
# MERGE PDF
# --------------------------------------------------

if tool == "Merge PDF":

    st.header("Merge PDF")

    uploaded_files = st.file_uploader(
        "Choose PDF files to merge",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:

        st.write(
            f"{len(uploaded_files)} PDF file(s) selected."
        )

        if st.button("Merge PDFs"):

            if len(uploaded_files) < 2:

                st.warning(
                    "Please select at least 2 PDF files to merge."
                )

            elif not can_use(user):

                st.warning(
                    "You've reached your 10 free operations "
                    "for this month."
                )

                st.info(
                    "Upgrade to PDF Toolbox Pro for more usage."
                )

            else:

                workspace = create_workspace()

                try:

                    input_paths = []

                    for index, uploaded_file in enumerate(
                        uploaded_files
                    ):

                        input_path = (
                            workspace / f"input_{index}.pdf"
                        )

                        with open(input_path, "wb") as file:
                            file.write(
                                uploaded_file.getbuffer()
                            )

                        input_paths.append(input_path)

                    output_path = (
                        workspace / "merged_result.pdf"
                    )

                    merge_pdfs(
                        input_paths,
                        output_path,
                    )

                    record_operation(user)

                    st.success(
                        "PDFs merged successfully."
                    )

                    with open(output_path, "rb") as file:

                        st.download_button(
                            label="Download merged PDF",
                            data=file,
                            file_name="merged_result.pdf",
                            mime="application/pdf",
                        )

                except Exception:

                    st.error(
                        "We couldn't merge those PDFs. "
                        "Please make sure the files are valid "
                        "PDF documents and try again."
                    )

                finally:

                    cleanup_workspace(workspace)


# --------------------------------------------------
# SPLIT PDF
# --------------------------------------------------

elif tool == "Split PDF":

    st.header("Split PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF to split",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "split_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            try:

                document = pymupdf.open(input_path)

                page_count = len(document)

                document.close()

            except Exception:

                st.error(
                    "We couldn't read this PDF. "
                    "Please upload a valid PDF document."
                )

                page_count = 0

            if page_count > 0:

                st.write(
                    f"This PDF contains **{page_count} page(s)**."
                )

                if st.button("Split PDF"):

                    if not can_use(user):

                        st.warning(
                            "You've reached your 10 free operations "
                            "for this month."
                        )

                        st.info(
                            "Upgrade to PDF Toolbox Pro for more usage."
                        )

                    else:

                        try:

                            output_paths = [
                                workspace / f"split_page_{i + 1}.pdf"
                                for i in range(page_count)
                            ]

                            split_pdf(
                                input_path,
                                output_paths,
                            )

                            record_operation(user)

                            st.success(
                                "PDF split successfully."
                            )

                            for index, output_path in enumerate(
                                output_paths
                            ):

                                with open(
                                    output_path,
                                    "rb"
                                ) as file:

                                    st.download_button(
                                        label=(
                                            f"Download page "
                                            f"{index + 1}"
                                        ),
                                        data=file,
                                        file_name=(
                                            f"page_{index + 1}.pdf"
                                        ),
                                        mime="application/pdf",
                                        key=(
                                            f"split_download_{index}"
                                        ),
                                    )

                        except Exception:

                            st.error(
                                "We couldn't split this PDF. "
                                "Please try another valid PDF."
                            )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# COMPRESS PDF
# --------------------------------------------------

elif tool == "Compress PDF":

    st.header("Compress PDF")

    if user["plan"] != "pro":

        st.info(
            "Compress PDF is a Pro feature."
        )

        st.write(
            "Upgrade to PDF Toolbox Pro for "
            "KSh 700/month."
        )

        if st.button(
            "Upgrade to Pro · KSh 700/month",
            use_container_width=True,
            key="upgrade_compress",
        ):
            checkout = start_pro_checkout()

            if checkout:
                st.link_button(
                    "Continue to secure payment",
                    checkout["authorization_url"],
                    use_container_width=True,
                )

        st.stop()

    uploaded_file = st.file_uploader(
        "Choose a PDF to compress",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "compress_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            original_size = input_path.stat().st_size

            if original_size > 0:

                st.write(
                    f"Original file size: "
                    f"**{original_size / 1024:.1f} KB**"
                )

            if st.button("Compress PDF"):

                if not can_use(user):

                    st.warning(
                        "You've reached your 150 Pro operations "
                        "for this month."
                    )

                else:

                    try:

                        output_path = (
                            workspace
                            / "compressed_result.pdf"
                        )

                        compress_pdf(
                            input_path,
                            output_path,
                        )

                        compressed_size = (
                            output_path.stat().st_size
                        )

                        record_operation(user)

                        st.success(
                            "PDF compression complete."
                        )

                        st.write(
                            f"Compressed file size: "
                            f"**{compressed_size / 1024:.1f} KB**"
                        )

                        if compressed_size < original_size:

                            reduction = (
                                (
                                    original_size
                                    - compressed_size
                                )
                                / original_size
                            ) * 100

                            st.write(
                                f"Size reduction: "
                                f"**{reduction:.1f}%**"
                            )

                        else:

                            st.info(
                                "This PDF could not be reduced "
                                "further with the current compression method."
                            )

                        with open(output_path, "rb") as file:

                            st.download_button(
                                label="Download compressed PDF",
                                data=file,
                                file_name="compressed_result.pdf",
                                mime="application/pdf",
                            )

                    except Exception:

                        st.error(
                            "We couldn't compress this PDF. "
                            "Please try another valid PDF."
                        )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# REORDER / DELETE PAGES
# --------------------------------------------------

elif tool == "Reorder / Delete Pages":

    st.header("Reorder / Delete Pages")

    # ----------------------------------------------
    # PRO GATE
    # ----------------------------------------------

    if user["plan"] != "pro":

        st.info(
            "Reorder / Delete Pages is a Pro feature."
        )

        st.write(
            "Upgrade to PDF Toolbox Pro for "
            "KSh 700/month."
        )

        if st.button(
            "Upgrade to Pro · KSh 700/month",
            use_container_width=True,
            key="upgrade_reorder",
        ):

            checkout = start_pro_checkout()

            if checkout:

                st.link_button(
                    "Continue to secure payment",
                    checkout["authorization_url"],
                    use_container_width=True,
                )

        st.stop()

    # ----------------------------------------------
    # PRO TOOL
    # ----------------------------------------------

    uploaded_file = st.file_uploader(
        "Choose a PDF",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "reorder_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            try:

                document = pymupdf.open(input_path)

                page_count = len(document)

                document.close()

            except Exception:

                st.error(
                    "We couldn't read this PDF. "
                    "Please upload a valid PDF document."
                )

                page_count = 0

            if page_count > 0:

                st.write(
                    f"This PDF contains **{page_count} page(s)**."
                )

                st.caption(
                    "Enter the page numbers in the order "
                    "you want them. Leave out a page number "
                    "to delete that page."
                )

                page_order_text = st.text_input(
                    "New page order",
                    placeholder="Example: 3,1,4",
                )

                if st.button("Apply Changes"):

                    if not can_use(user):

                        st.warning(
                            "You've reached your 150 Pro operations "
                            "for this month."
                        )

                    else:

                        try:

                            page_order = [
                                int(page.strip()) - 1
                                for page in page_order_text.split(",")
                                if page.strip()
                            ]

                            if not page_order:

                                st.warning(
                                    "Enter at least one page number."
                                )

                            elif any(
                                page < 0 or page >= page_count
                                for page in page_order
                            ):

                                st.error(
                                    "One or more page numbers are "
                                    "outside the range of this PDF."
                                )

                            elif len(page_order) != len(set(page_order)):

                                st.error(
                                    "Each page can only appear once."
                                )

                            else:

                                output_path = (
                                    workspace
                                    / "reordered_result.pdf"
                                )

                                reorder_pages(
                                    input_path,
                                    output_path,
                                    page_order,
                                )

                                record_operation(user)

                                st.success(
                                    "PDF pages updated successfully."
                                )

                                with open(
                                    output_path,
                                    "rb"
                                ) as file:

                                    st.download_button(
                                        label="Download updated PDF",
                                        data=file,
                                        file_name=(
                                            "reordered_result.pdf"
                                        ),
                                        mime="application/pdf",
                                    )

                        except ValueError:

                            st.error(
                                "Please enter page numbers "
                                "using numbers separated by commas."
                            )

                        except Exception:

                            st.error(
                                "We couldn't update this PDF. "
                                "Please try another valid PDF."
                            )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# ROTATE PDF
# --------------------------------------------------

elif tool == "Rotate PDF":

    st.header("Rotate PDF")

    uploaded_file = st.file_uploader(
        "Choose a PDF to rotate",
        type=["pdf"],
    )

    if uploaded_file:

        workspace = create_workspace()

        try:

            input_path = (
                workspace / "rotate_input.pdf"
            )

            with open(input_path, "wb") as file:
                file.write(
                    uploaded_file.getbuffer()
                )

            rotation = st.selectbox(
                "Rotation",
                [90, 180, 270],
                format_func=lambda value:
                    f"{value}° clockwise",
            )

            if st.button("Rotate PDF"):

                if not can_use(user):

                    st.warning(
                        "You've reached your 10 free operations "
                        "for this month."
                    )

                    st.info(
                        "Upgrade to PDF Toolbox Pro for more usage."
                    )

                else:

                    try:

                        output_path = (
                            workspace
                            / "rotated_result.pdf"
                        )

                        rotate_pdf(
                            input_path,
                            output_path,
                            rotation=rotation,
                        )

                        record_operation(user)

                        st.success(
                            f"PDF rotated "
                            f"{rotation}° clockwise."
                        )

                        with open(
                            output_path,
                            "rb"
                        ) as file:

                            st.download_button(
                                label="Download rotated PDF",
                                data=file,
                                file_name="rotated_result.pdf",
                                mime="application/pdf",
                            )

                    except Exception:

                        st.error(
                            "We couldn't rotate this PDF. "
                            "Please try another valid PDF."
                        )

        finally:

            cleanup_workspace(workspace)


# --------------------------------------------------
# IMAGES → PDF
# --------------------------------------------------

elif tool == "Images → PDF":

    st.header("Images → PDF")

    uploaded_files = st.file_uploader(
        "Choose images",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if uploaded_files:

        st.write(
            f"{len(uploaded_files)} image(s) selected."
        )

        if st.button("Convert to PDF"):

            if not can_use(user):

                st.warning(
                    "You've reached your 10 free operations "
                    "for this month."
                )

                st.info(
                    "Upgrade to PDF Toolbox Pro for more usage."
                )

            else:

                workspace = create_workspace()

                try:

                    input_paths = []

                    for index, uploaded_file in enumerate(
                        uploaded_files
                    ):

                        input_path = (
                            workspace
                            / (
                                f"image_{index}_"
                                f"{uploaded_file.name}"
                            )
                        )

                        with open(
                            input_path,
                            "wb"
                        ) as file:

                            file.write(
                                uploaded_file.getbuffer()
                            )

                        input_paths.append(input_path)

                    output_path = (
                        workspace / "images_result.pdf"
                    )

                    try:

                        images_to_pdf(
                            input_paths,
                            output_path,
                        )

                        record_operation(user)

                        st.success(
                            "Images converted to PDF successfully."
                        )

                        with open(
                            output_path,
                            "rb"
                        ) as file:

                            st.download_button(
                                label="Download PDF",
                                data=file,
                                file_name="images_result.pdf",
                                mime="application/pdf",
                            )

                    except Exception:

                        st.error(
                            "We couldn't convert these images "
                            "to PDF. Please check the image files "
                            "and try again."
                        )

                finally:

                    cleanup_workspace(workspace)

st.divider()

st.caption(
    "PDF Toolbox • Simple document tools for everyday PDF tasks."
)