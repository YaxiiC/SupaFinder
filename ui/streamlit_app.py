"""Streamlit UI for PhD Supervisor Finder with subscription support."""

import streamlit as st
import tempfile
from pathlib import Path
import re
import sys
import os

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Initialize session state
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# Handle payment success callback
if "payment" in st.query_params and st.query_params["payment"] == "success":
    session_id = st.query_params.get("session_id")
    if session_id:
        try:
            from app.modules.payment import handle_payment_success
            from app.modules.subscription import create_subscription
            from app.db_cloud import init_db
            
            payment_info = handle_payment_success(session_id)
            subscription_type = payment_info.get('metadata', {}).get('subscription_type')
            
            if subscription_type and st.session_state.user_id:
                init_db()
                subscription_id = create_subscription(st.session_state.user_id, subscription_type)
                st.success("✅ Payment successful! Subscription activated.")
                # Clear query params
                st.query_params.clear()
                st.rerun()
        except Exception as e:
            st.error(f"Payment processing error: {e}")

st.set_page_config(
    page_title="PhD Supervisor Finder",
    page_icon="🎓",
    layout="wide"
)

# Sidebar for authentication and subscription
with st.sidebar:
    st.header("🔐 Account")
    
    if st.session_state.user_email:
        st.success(f"Logged in as: {st.session_state.user_email}")
        
        # Check if developer
        from app.modules.subscription import get_user_subscription, is_developer, is_beta_user, get_beta_free_searches_remaining
        is_dev = is_developer(st.session_state.user_email)
        is_beta = is_beta_user(st.session_state.user_email)
        
        if is_dev:
            st.success("🔧 **Developer Mode** - Unlimited access")
        elif is_beta:
            # Check beta user status
            beta_searches = get_beta_free_searches_remaining(st.session_state.user_id)
            if beta_searches is not None and beta_searches > 0:
                st.info(f"🧪 **Beta User** - {beta_searches} free searches remaining")
            else:
                st.warning("🧪 **Beta User** - Free searches used up")
            
            # Also show subscription if they have one
            subscription = get_user_subscription(st.session_state.user_id)
            if subscription:
                st.subheader("📊 Subscription")
                st.write(f"**Plan:** {subscription['type'].title()}")
                st.write(f"**Remaining searches:** {subscription['remaining_searches']}/{subscription['searches_per_month']}")
                
                from datetime import datetime
                expires_at = subscription['expires_at']
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                st.write(f"**Expires:** {expires_at.strftime('%Y-%m-%d')}")
        else:
            # Get subscription info
            subscription = get_user_subscription(st.session_state.user_id)
            
            if subscription:
                st.subheader("📊 Subscription")
                st.write(f"**Plan:** {subscription['type'].title()}")
                st.write(f"**Remaining searches:** {subscription['remaining_searches']}/{subscription['searches_per_month']}")
                
                from datetime import datetime
                expires_at = subscription['expires_at']
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                st.write(f"**Expires:** {expires_at.strftime('%Y-%m-%d')}")
            else:
                st.warning("No active subscription")
        
        # Subscription management button
        if st.button("💳 Manage Subscription", use_container_width=True):
            st.session_state.show_subscription_page = True
        
        if st.button("📜 Search History", use_container_width=True):
            st.session_state.show_history_page = True
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_email = None
            st.session_state.user_id = None
            st.session_state.show_subscription_page = False
            st.session_state.show_history_page = False
            st.rerun()
    else:
        st.info("Please log in to use the service")
        
        # Email/Password Login
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="your.email@example.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
                submit_login = st.form_submit_button("Login", use_container_width=True)
            
            if submit_login:
                if email and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    try:
                        from app.modules.auth import verify_user_password, user_has_password
                        from app.modules.subscription import get_or_create_user
                        from app.db_cloud import init_db
                        init_db()
                        
                        email_lower = email.lower().strip()
                        
                        # Security: Password is always required for login
                        if not password:
                            st.error("Password is required. Please enter your password or register a new account.")
                        else:
                            # Check if user exists and verify password
                            from app.modules.auth import verify_user_password, user_exists
                            
                            if not user_exists(email_lower):
                                # User doesn't exist - redirect to registration
                                st.warning("Account not found. Please register a new account using the 'Register' tab.")
                            else:
                                # User exists - verify password (password is always required)
                                is_valid, user_id = verify_user_password(email_lower, password)
                                if is_valid:
                                    st.session_state.user_email = email_lower
                                    st.session_state.user_id = user_id
                                    st.success("Logged in successfully!")
                                    st.rerun()
                                else:
                                    st.error("Invalid email or password. If you haven't set a password yet, please register first.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Please enter a valid email address")
        
        with register_tab:
            with st.form("register_form"):
                st.info("Create a new account with email and password")
                reg_email = st.text_input("Email", placeholder="your.email@example.com", key="reg_email")
                reg_password = st.text_input("Password", type="password", placeholder="At least 8 characters", key="reg_password")
                reg_password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="reg_password_confirm")
                submit_register = st.form_submit_button("Register", use_container_width=True)
                
                if submit_register:
                    if reg_email and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', reg_email):
                        if reg_password:
                            # Validate password
                            from app.modules.auth import validate_password_strength, set_user_password, user_has_password
                            from app.modules.subscription import get_or_create_user
                            from app.db_cloud import init_db
                            init_db()
                            
                            is_valid, error_msg = validate_password_strength(reg_password)
                            if not is_valid:
                                st.error(error_msg)
                            elif reg_password != reg_password_confirm:
                                st.error("Passwords do not match")
                            else:
                                try:
                                    reg_email_lower = reg_email.lower().strip()
                                    
                                    # Check if user already exists
                                    if user_has_password(reg_email_lower):
                                        st.error("This email is already registered. Please login instead.")
                                    else:
                                        # Create user or get existing user
                                        user_id = get_or_create_user(reg_email_lower)
                                        
                                        # Set password
                                        set_user_password(user_id, reg_password)
                                        
                                        st.session_state.user_email = reg_email_lower
                                        st.session_state.user_id = user_id
                                        st.success("Account created successfully! You are now logged in.")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        else:
                            st.error("Please enter a password")
                    else:
                        st.error("Please enter a valid email address")

# Main content
if st.session_state.get("show_subscription_page"):
    st.title("💳 Subscription Management")
    st.divider()
    
    if not st.session_state.user_email:
        st.error("Please log in first")
        st.stop()
    
    # Get current subscription
    from app.modules.subscription import get_user_subscription, PLANS, create_subscription
    subscription = get_user_subscription(st.session_state.user_id)
    
    if subscription:
        st.success(f"You currently have an **{subscription['type'].title()}** subscription")
        st.write(f"- Remaining searches: {subscription['remaining_searches']}/{subscription['searches_per_month']}")
        
        from datetime import datetime
        expires_at = subscription['expires_at']
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        st.write(f"- Expires: {expires_at.strftime('%Y-%m-%d')}")
    else:
        st.info("You don't have an active subscription")
    
    st.divider()
    st.subheader("Available Plans")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Individual Plan")
        st.write(f"**£{PLANS['individual']['price_usd']}/month**")
        st.write(f"- {PLANS['individual']['searches_per_month']} searches per month")
        st.write("- Perfect for personal use")
        
        # Check if Stripe is fully configured
        stripe_configured = False
        stripe_error = None
        try:
            from app.modules.payment import get_stripe_client, create_checkout_session
            # Test if we can get the client
            get_stripe_client()
            # Test if we can create a session (this checks Price IDs too)
            try:
                # Just check if price IDs are configured, don't actually create session
                from app.config import get_secret
                price_id = get_secret("STRIPE_PRICE_ID_INDIVIDUAL", "")
                if not price_id:
                    stripe_error = "STRIPE_PRICE_ID_INDIVIDUAL not configured in Streamlit Secrets"
                else:
                    stripe_configured = True
            except Exception as e:
                stripe_error = f"Stripe configuration error: {e}"
        except ImportError:
            stripe_error = "stripe package not installed"
        except Exception as e:
            stripe_error = f"Stripe not configured: {e}"
        
        if stripe_configured:
            # Use Stripe payment - REQUIRED
            if st.button("💳 Subscribe with Payment - Individual", key="subscribe_individual", use_container_width=True):
                try:
                    import urllib.parse
                    from app.config import get_secret
                    
                    # Get current URL for redirect - must be full URL
                    # Option 1: From Streamlit Secrets (recommended)
                    app_url = get_secret("APP_URL", "")
                    
                    # Option 2: Try to construct from environment
                    if not app_url:
                        # Try to get from Streamlit config
                        try:
                            server_name = st.get_option("server.headless")  # Not ideal, try other methods
                            # Fall back to constructing from known Streamlit Cloud pattern
                            # User should set APP_URL in secrets
                            app_url = "https://supafinder.streamlit.app"
                        except:
                            app_url = "https://supafinder.streamlit.app"
                    
                    # Ensure URL doesn't end with /
                    app_url = app_url.rstrip('/')
                    
                    success_url = f"{app_url}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
                    cancel_url = f"{app_url}/?payment=cancelled"
                    
                    session = create_checkout_session(
                        user_email=st.session_state.user_email,
                        subscription_type="individual",
                        success_url=success_url,
                        cancel_url=cancel_url
                    )
                    
                    if session and session.get('url'):
                        st.info("Redirecting to payment page...")
                        st.markdown(f"[Click here to complete payment]({session['url']})")
                        st.session_state['stripe_session_id'] = session['id']
                    else:
                        st.error("Failed to create payment session. Please contact support.")
                except Exception as e:
                    st.error(f"Payment error: {e}")
                    st.info("Please check your Stripe configuration in Streamlit Secrets.")
        else:
            # Payment REQUIRED - show error instead of allowing free subscription
            st.error("❌ Payment system not configured")
            if stripe_error:
                st.warning(f"**Error:** {stripe_error}")
            st.info("""
            **To enable subscriptions, please configure:**
            1. `STRIPE_SECRET_KEY` in Streamlit Secrets
            2. `STRIPE_PRICE_ID_INDIVIDUAL` in Streamlit Secrets
            3. Create the price in Stripe Dashboard
            
            See `STRIPE_SETUP.md` for detailed instructions.
            """)
            st.button("Subscribe - Individual", key="subscribe_individual", disabled=True, use_container_width=True)
    
    with col2:
        st.markdown("### 🏢 Enterprise Plan")
        st.write(f"**£{PLANS['enterprise']['price_usd']}/month**")
        st.write(f"- {PLANS['enterprise']['searches_per_month']} searches per month")
        st.write("- Ideal for teams and organizations")
        
        # Check if Stripe is fully configured
        stripe_configured = False
        stripe_error = None
        try:
            from app.modules.payment import get_stripe_client, create_checkout_session
            # Test if we can get the client
            get_stripe_client()
            # Test if we can create a session (this checks Price IDs too)
            try:
                # Just check if price IDs are configured, don't actually create session
                from app.config import get_secret
                price_id = get_secret("STRIPE_PRICE_ID_ENTERPRISE", "")
                if not price_id:
                    stripe_error = "STRIPE_PRICE_ID_ENTERPRISE not configured in Streamlit Secrets"
                else:
                    stripe_configured = True
            except Exception as e:
                stripe_error = f"Stripe configuration error: {e}"
        except ImportError:
            stripe_error = "stripe package not installed"
        except Exception as e:
            stripe_error = f"Stripe not configured: {e}"
        
        if stripe_configured:
            # Use Stripe payment - REQUIRED
            if st.button("💳 Subscribe with Payment - Enterprise", key="subscribe_enterprise", use_container_width=True):
                try:
                    import urllib.parse
                    from app.config import get_secret
                    
                    # Get current URL for redirect - must be full URL
                    # Option 1: From Streamlit Secrets (recommended)
                    app_url = get_secret("APP_URL", "")
                    
                    # Option 2: Try to construct from environment
                    if not app_url:
                        # Fall back to constructing from known Streamlit Cloud pattern
                        app_url = "https://supafinder.streamlit.app"
                    
                    # Ensure URL doesn't end with /
                    app_url = app_url.rstrip('/')
                    
                    success_url = f"{app_url}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
                    cancel_url = f"{app_url}/?payment=cancelled"
                    
                    session = create_checkout_session(
                        user_email=st.session_state.user_email,
                        subscription_type="enterprise",
                        success_url=success_url,
                        cancel_url=cancel_url
                    )
                    
                    if session and session.get('url'):
                        st.info("Redirecting to payment page...")
                        st.markdown(f"[Click here to complete payment]({session['url']})")
                        st.session_state['stripe_session_id'] = session['id']
                    else:
                        st.error("Failed to create payment session. Please contact support.")
                except Exception as e:
                    st.error(f"Payment error: {e}")
                    st.info("Please check your Stripe configuration in Streamlit Secrets.")
        else:
            # Payment REQUIRED - show error instead of allowing free subscription
            st.error("❌ Payment system not configured")
            if stripe_error:
                st.warning(f"**Error:** {stripe_error}")
            st.info("""
            **To enable subscriptions, please configure:**
            1. `STRIPE_SECRET_KEY` in Streamlit Secrets
            2. `STRIPE_PRICE_ID_ENTERPRISE` in Streamlit Secrets
            3. Create the price in Stripe Dashboard
            
            See `STRIPE_SETUP.md` for detailed instructions.
            """)
            st.button("Subscribe - Enterprise", key="subscribe_enterprise", disabled=True, use_container_width=True)
    
    if st.button("← Back to Main", use_container_width=True):
        st.session_state.show_subscription_page = False
        st.rerun()

elif st.session_state.get("show_history_page"):
    st.title("📜 Search History")
    st.divider()
    
    if not st.session_state.user_email:
        st.error("Please log in first")
        st.stop()
    
    from app.modules.subscription import get_user_search_history
    history = get_user_search_history(st.session_state.user_id, limit=50)
    
    if history:
        for search in history:
            with st.expander(f"🔍 {search['keywords'][:50]}... ({search['created_at']})"):
                st.write(f"**Type:** {search['type']}")
                st.write(f"**Keywords:** {search['keywords']}")
                st.write(f"**Results:** {search['result_count']}")
                st.write(f"**Date:** {search['created_at']}")
    else:
        st.info("No search history yet")
    
    if st.button("← Back to Main", use_container_width=True):
        st.session_state.show_history_page = False
        st.rerun()

else:
    # Main search interface
    st.title("🎓 PhD Supervisor Finder")
    st.markdown("*AI-assisted PhD supervisor discovery*")
    
    if not st.session_state.user_email:
        st.warning("⚠️ Please log in using the sidebar to use the service. First-time users get 1 free search!")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Your CV (Optional)")
        st.caption("You can upload a CV, enter keywords, or both")
        cv_file = st.file_uploader("Upload your CV (PDF or TXT)", type=["pdf", "txt"], help="Optional: Upload your CV to extract research interests automatically")
        
        st.subheader("🔬 Research Keywords (Optional)")
        keywords = st.text_area(
            "Enter your research keywords (comma-separated)",
            placeholder="e.g., psychology, social sciences, behavioral sciences, cognitive sciences, human development, developmental psychology",
            height=100,
            help="Optional: Enter your research keywords. At least one of CV or keywords is required."
        )
    
    with col2:
        st.subheader("🏛️ Universities")
        st.info("Using built-in universities list (QS Rank Top 200+ universities worldwide)")
        
        st.subheader("🎯 Filters")
        
        regions = st.text_input(
            "Regions (comma-separated)",
            placeholder="e.g., Europe, North America, Asia"
        )
        
        countries = st.text_input(
            "Countries (comma-separated)",
            placeholder="e.g., Singapore, Sweden, United Kingdom"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            qs_max = st.number_input("Max QS Rank", min_value=1, max_value=1000, value=100)
        with col_b:
            target = st.number_input("Target Supervisors", min_value=10, max_value=500, value=100)
        
        local_first = st.checkbox("Use local DB first (recommended)", value=True)
    
    st.divider()
    
    if st.button("🚀 Find Supervisors", type="primary", use_container_width=True):
        # Debug: Check button click
        st.write("🔴 DEBUG: Button clicked!")
        
        if not st.session_state.user_email:
            st.error("Please log in first using the sidebar")
            st.write("🔴 DEBUG: User not logged in")
        elif not cv_file and not keywords:
            st.error("Please upload a CV or enter research keywords (at least one is required)")
            st.write("🔴 DEBUG: No CV or keywords provided")
        else:
            st.write("🔴 DEBUG: Starting search process...")
            st.write(f"🔴 DEBUG: User email: {st.session_state.user_email}")
            st.write(f"🔴 DEBUG: User ID: {st.session_state.user_id}")
            st.write(f"🔴 DEBUG: Has CV: {cv_file is not None}")
            st.write(f"🔴 DEBUG: Keywords: {keywords[:50] if keywords else 'None'}")
            
            # Create progress tracking components
            progress_bar = st.progress(0)
            status_text = st.empty()
            stats_text = st.empty()
            
            # Progress callback function
            def update_progress(step: str, progress: float, message: str, **kwargs):
                """Update Streamlit progress display."""
                progress_bar.progress(min(progress, 1.0))
                status_text.info(f"📊 **Current Step:** {message}")
                
                if "found_count" in kwargs:
                    stats_text.success(f"✅ **Progress:** Found {kwargs['found_count']} supervisors so far")
            
            try:
                st.write("🔴 DEBUG: Entered try block")
                
                # Initialize status
                status_text.info("🔍 Starting search...")
                st.write("🔴 DEBUG: Status initialized")
                
                # Use built-in universities template
                from app.config import DATA_DIR
                uni_path = DATA_DIR / "universities_template.xlsx"
                st.write(f"🔴 DEBUG: University path: {uni_path}")
                
                if not uni_path.exists():
                    st.error(f"Universities template not found at {uni_path}")
                    st.stop()
                
                status_text.info("📁 Preparing files...")
                st.write("🔴 DEBUG: Preparing files...")
                
                # Save uploaded CV to temp directory if provided
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmpdir = Path(tmpdir)
                    
                    # Save CV if provided
                    cv_path = None
                    if cv_file:
                        cv_path = tmpdir / cv_file.name
                        cv_path.write_bytes(cv_file.read())
                    
                    # Output path
                    output_path = tmpdir / "supervisors.xlsx"
                    
                    # Parse regions
                    regions_list = [r.strip() for r in regions.split(",")] if regions else None
                    
                    # Parse countries
                    countries_list = [c.strip() for c in countries.split(",")] if countries else None
                    
                    # Import and run pipeline
                    status_text.info("🔧 Initializing pipeline...")
                    st.write("🔴 DEBUG: Initializing pipeline...")
                    from app.pipeline import run_pipeline
                    from app.db_cloud import init_db
                    import inspect
                    init_db()
                    st.write("🔴 DEBUG: Database initialized")
                    
                    # Check subscription before running
                    if st.session_state.user_id:
                        st.write("🔴 DEBUG: Checking subscription...")
                        from app.modules.subscription import can_perform_search
                        can_search, error_msg, sub_info = can_perform_search(st.session_state.user_id)
                        if not can_search:
                            st.error(f"❌ {error_msg}")
                            if "subscription" in error_msg.lower() or "searches" in error_msg.lower():
                                if st.button("💳 Go to Subscription Page", use_container_width=True):
                                    st.session_state.show_subscription_page = True
                                    st.rerun()
                            st.stop()
                        st.write(f"🔴 DEBUG: Subscription check passed. Remaining: {sub_info.get('remaining_searches', 'N/A')}")
                        status_text.info(f"✅ Subscription check passed. Remaining searches: {sub_info.get('remaining_searches', 'N/A')}")
                    
                    # Check if run_pipeline accepts progress_callback parameter
                    # This provides compatibility if Streamlit Cloud hasn't updated yet
                    st.write("🔴 DEBUG: Preparing pipeline arguments...")
                    sig = inspect.signature(run_pipeline)
                    kwargs = {
                        "cv_path": cv_path,
                        "keywords": keywords.strip() if keywords else None,
                        "universities_path": uni_path,
                        "output_path": output_path,
                        "regions": regions_list,
                        "countries": countries_list,
                        "qs_max": qs_max if qs_max else None,
                        "target": target,
                        "local_first": local_first,
                        "user_id": st.session_state.user_id,
                    }
                    
                    # Only add progress_callback if the function accepts it
                    if "progress_callback" in sig.parameters:
                        kwargs["progress_callback"] = update_progress
                    
                    st.write("🔴 DEBUG: Calling run_pipeline...")
                    status_text.info("🚀 Running pipeline...")
                    run_pipeline(**kwargs)
                    st.write("🔴 DEBUG: Pipeline completed!")
                    
                    # Clear progress indicators
                    progress_bar.progress(1.0)
                    status_text.empty()
                    stats_text.empty()
                    
                    # Read output and provide download
                    if output_path.exists():
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Results (Excel)",
                                data=f.read(),
                                file_name="supervisors.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        st.success("✅ Pipeline completed successfully!")
                        
                        # Show updated subscription info
                        from app.modules.subscription import get_user_subscription
                        subscription = get_user_subscription(st.session_state.user_id)
                        if subscription:
                            st.info(f"Remaining searches: {subscription['remaining_searches']}/{subscription['searches_per_month']}")
                    else:
                        st.error("No output file generated")
            
            except ValueError as e:
                # Subscription-related errors
                st.write(f"🔴 DEBUG: ValueError caught: {e}")
                st.error(str(e))
                if "subscription" in str(e).lower() or "searches" in str(e).lower():
                    if st.button("💳 Go to Subscription Page", use_container_width=True):
                        st.session_state.show_subscription_page = True
                        st.rerun()
            except Exception as e:
                st.write(f"🔴 DEBUG: Exception caught: {e}")
                st.error(f"Error running pipeline: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    st.divider()
    st.caption("PhD Supervisor Finder • LLM-first approach using DeepSeek")
