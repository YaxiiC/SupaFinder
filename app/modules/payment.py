"""Payment processing module using Stripe."""

import os
from typing import Optional, Dict
from app.config import get_secret

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None


def get_stripe_client():
    """Get Stripe client instance."""
    if not STRIPE_AVAILABLE:
        raise ImportError("stripe package is required. Install with: pip install stripe")
    
    stripe_key = get_secret("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise ValueError("STRIPE_SECRET_KEY not configured. Please set it in Streamlit Secrets or .env file")
    
    stripe.api_key = stripe_key
    return stripe


def create_checkout_session(
    user_email: str,
    subscription_type: str,
    success_url: str,
    cancel_url: str
) -> Optional[Dict]:
    """
    Create a Stripe Checkout Session for subscription.
    
    Args:
        user_email: User's email address
        subscription_type: 'individual' or 'enterprise'
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled
    
    Returns:
        Checkout session object with 'id' and 'url'
    """
    if not STRIPE_AVAILABLE:
        raise ImportError("stripe package is required. Install with: pip install stripe")
    
    stripe_client = get_stripe_client()
    
    # Get price IDs from config (you need to create these in Stripe Dashboard)
    price_ids = {
        "individual": get_secret("STRIPE_PRICE_ID_INDIVIDUAL", ""),
        "enterprise": get_secret("STRIPE_PRICE_ID_ENTERPRISE", "")
    }
    
    price_id = price_ids.get(subscription_type)
    if not price_id:
        raise ValueError(f"Stripe price ID not configured for {subscription_type}. Please set STRIPE_PRICE_ID_{subscription_type.upper()} in Streamlit Secrets")
    
    try:
        session = stripe_client.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'subscription_type': subscription_type,
                'user_email': user_email
            }
        )
        
        return {
            'id': session.id,
            'url': session.url
        }
    except Exception as e:
        raise Exception(f"Failed to create Stripe checkout session: {e}")


def verify_webhook_signature(payload: str, signature: str, secret: str) -> Optional[Dict]:
    """
    Verify Stripe webhook signature.
    
    Args:
        payload: Raw request body
        signature: Stripe signature header
        secret: Webhook signing secret
    
    Returns:
        Event object if valid, None otherwise
    """
    if not STRIPE_AVAILABLE:
        raise ImportError("stripe package is required. Install with: pip install stripe")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, secret
        )
        return event
    except ValueError as e:
        raise ValueError(f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid signature: {e}")


def handle_payment_success(session_id: str) -> Dict:
    """
    Handle successful payment by retrieving checkout session.
    
    Args:
        session_id: Stripe checkout session ID
    
    Returns:
        Session object with customer and subscription info
    """
    if not STRIPE_AVAILABLE:
        raise ImportError("stripe package is required. Install with: pip install stripe")
    
    stripe_client = get_stripe_client()
    
    try:
        session = stripe_client.checkout.Session.retrieve(session_id)
        return {
            'customer_email': session.customer_email,
            'subscription_id': session.subscription,
            'metadata': session.metadata or {},
            'payment_status': session.payment_status
        }
    except Exception as e:
        raise Exception(f"Failed to retrieve checkout session: {e}")

